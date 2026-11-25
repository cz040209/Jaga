"""Offline MYR event simulation. Run from ml/ with uv run python synthetic/generate.py.

Only emitted payments become rows. Logins, payee additions, credits, password
changes and delayed reports update state separately. Features precede payment
settlement and label assignment. No connection to Jaga's application or database.
"""

from __future__ import annotations

import argparse
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import hashlib
import heapq
import json
from pathlib import Path

import numpy as np
import pandas as pd


GROUPS = {
    "Metadata": "event_id customer_id payee_id event_time scenario",
    "Transaction and calendar": "amount channel transaction_type hour_of_day day_of_week is_salary_period is_festive_period",
    "Amount versus history": "amount_vs_median_ratio amount_zscore_90d balance_before pct_balance_drained",
    "Velocity": "txn_count_5m txn_count_1h txn_count_24h txn_amount_1h txn_amount_24h distinct_payees_24h failed_logins_24h",
    "Payee": "payee_age_minutes is_first_transfer_to_payee payee_account_age_days payee_inbound_senders_24h payee_on_watchlist",
    "Device and security": "is_new_device device_age_days is_new_location km_from_usual_location minutes_since_password_change minutes_since_login",
    "Network": "ip_is_foreign ip_is_hosting_or_vpn timezone_mismatch is_emulator_or_headless devices_seen_7d device_shared_by_customers",
    "Behaviour": "seconds_on_amount_screen account_number_pasted session_actions_before_transfer typing_cadence_distance hesitation_before_confirm_ms hold_to_send_attempts app_switches_during_transfer",
    "Graph": "payee_fan_in_7d payee_pass_through_ratio payee_hops_to_known_fraud payee_shared_by_victims",
    "Note": "note_scam_keyword_hits note_similarity_to_known_scams note_is_empty",
    "History": "customer_age_days minutes_since_last_txn amount_trend_last_5 same_amount_repeats_24h night_activity_ratio_30d previous_holds_30d previous_fraud_reports",
    "Agent signals": "scam_interview_red_flags customer_said_not_me scam_message_checked_recently otp_failures_24h",
    "Labels": "is_fraud fraud_type victim_coached loss_amount label_source",
}
INTERNAL_COLUMNS = [name for group in GROUPS.values() for name in group.split()]
REMOVED = {"channel", "day_of_week", "is_salary_period", "amount_zscore_90d",
           "txn_amount_1h", "timezone_mismatch", "session_actions_before_transfer",
           "note_is_empty", "scam_interview_red_flags", "customer_said_not_me", "label_source"}
COLUMNS = [name for name in INTERNAL_COLUMNS if name not in REMOVED]
FEATURES = COLUMNS[5:-4]
DEFAULTS = dict.fromkeys(FEATURES, 0)
DEFAULTS.update(transaction_type="transfer", amount_vs_median_ratio=1.0,
                pct_balance_drained=0.0, payee_pass_through_ratio=1.0,
                is_first_transfer_to_payee=1, is_new_device=1,
                minutes_since_last_txn=525600, minutes_since_password_change=525600,
                minutes_since_login=525600, payee_hops_to_known_fraud=99)
FRAUD_TYPES = ["scam_macau", "scam_investment", "scam_job", "scam_love",
               "account_takeover", "mule", "card_testing"]
START = datetime(2025, 1, 1, tzinfo=timezone(timedelta(hours=8)))
# Fixed 2025 demonstration windows, not a general Malaysian holiday calendar.
FESTIVALS = [(datetime(2025, 1, 29), 7), (datetime(2025, 3, 31), 10),
             (datetime(2025, 10, 20), 7)]
KEYWORDS = ("lhdn", "polis", "pelaburan", "安全账户", "task", "investment")


def festive(date: datetime) -> bool:
    return any(abs((date.replace(tzinfo=None) - day).days) <= radius
               for day, radius in FESTIVALS)


@dataclass
class Customer:
    persona: str
    typical: float
    salary: float
    born: float
    balance: float
    device: int
    device_since: float
    saved: dict[int, float] = field(default_factory=dict)
    history: deque = field(default_factory=deque)
    failures: deque = field(default_factory=deque)
    otp: deque = field(default_factory=deque)
    holds: deque = field(default_factory=deque)
    devices: deque = field(default_factory=deque)
    password: float | None = None
    login: float = 0
    reports: int = 0
    paid_payees: set[int] = field(default_factory=set)


class Simulation:
    def __init__(self, customers: int, days: int, seed: int):
        self.rng = np.random.default_rng(seed)
        self.days = days
        self.end = days * 1440
        self.queue = []
        self.serial = 0
        self.rows = []
        self.truth = []
        self.known = set()
        self.known_victims = set()
        self.watchlist = set()
        self.graph = defaultdict(deque)
        self.outgoing = defaultdict(deque)
        self.edges = defaultdict(set)
        self.device_users = defaultdict(set)
        self.accounts = {}
        self.people = {}
        self.feature_future_reads = 0
        for cid in range(1, customers + 1):
            persona = str(self.rng.choice(["student", "salaried", "elderly", "trader", "gig"],
                                          p=[.20, .35, .15, .15, .15]))
            index = ["student", "salaried", "elderly", "trader", "gig"].index(persona)
            typical = float(self.rng.lognormal(np.log([40, 100, 75, 230, 65][index]), .5))
            self.people[cid] = Customer(persona, typical, typical * 45,
                -float(self.rng.uniform(0, 1500) * 1440), typical * 120,
                cid, -float(self.rng.uniform(1, 500) * 1440))
            self.accounts[cid] = self.people[cid].born
            for pid in self.rng.integers(customers + 1, customers * 4 + 1, 6):
                self.people[cid].saved[int(pid)] = -float(self.rng.uniform(1, 500) * 1440)
        for pid in range(customers + 1, customers * 4 + 101):
            self.accounts[pid] = -float(self.rng.uniform(0, 1800) * 1440)
            if self.rng.random() < .012:
                self.watchlist.add(pid)  # False/stale entries exist before any fraud.
        self.customer_count = customers

    def add(self, time: float, kind: str, cid: int, **data):
        if 0 <= time < self.end:
            self.serial += 1
            heapq.heappush(self.queue, (time, self.serial, kind, cid, data))

    def prepare(self):
        r = self.rng
        for day in range(self.days):
            date = START + timedelta(days=day)
            month = day // 30
            wave = [0.75, 1.0, .85, 1.8, 1.05, 1.35][min(month, 5)]
            for cid, c in self.people.items():
                if date.day == 25:
                    self.add(day * 1440 + 480, "credit", cid, amount=c.salary * r.uniform(.8, 1.2))
                rate = {"student": .36, "salaried": .40, "elderly": .22,
                        "trader": .80, "gig": .52}[c.persona]
                count = r.poisson(2.35 * rate * (1.25 if festive(date) else 1) * r.lognormal(-.18, .6))
                for _ in range(count):
                    hour = float(r.uniform(0, 24)) if r.random() < .18 else float(r.normal(17, 4) % 24)
                    if c.persona == "student":
                        hour = (hour + 2) % 24
                    t = day * 1440 + hour * 60
                    hard = r.random() < .075
                    scenario = str(r.choice(["rent_deposit", "contractor", "raya_remittance",
                        "new_phone", "travel", "urgent_child_topup"])) if hard else "routine"
                    # Genuine merchant/customer payments frequently reach new recipients.
                    pid = int(r.choice(list(c.saved))) if not hard and r.random() < .72 else int(r.integers(1, self.customer_count * 4))
                    if pid == cid:
                        pid = self.customer_count * 4
                    self.add(max(0, t - r.uniform(1, 500)), "save", cid, pid=pid)
                    amount = c.typical * r.lognormal(0, .9)
                    if scenario in ("rent_deposit", "contractor", "raya_remittance"):
                        amount *= r.uniform(7, 35)
                    if r.random() < .003:
                        amount *= r.uniform(40, 150)
                    self.login(t, cid, new=r.random() < .035 or scenario == "new_phone",
                               password=r.random() < .025)
                    self.add(t, "pay", cid, pid=pid, amount=amount, scenario=scenario,
                             attack=False, quiet=False, coached=False, step=0)
                # Campaign arrival rate varies over calendar time, independently of labels.
                if r.random() < .0059 * wave:
                    weights = np.array([3 if c.persona == "elderly" else 1.8, 2 if day > 80 else 1,
                                        1, 1, 1.8, .6, .5], dtype=float)
                    typ = str(r.choice(FRAUD_TYPES, p=weights / weights.sum()))
                    self.campaign(day, cid, typ)

    def login(self, t, cid, new=False, password=False):
        lag = float(self.rng.uniform(.3, 25))
        self.add(max(0, t - lag), "login", cid, new=bool(new))
        if password:
            self.add(max(0, t - lag / 2), "password", cid)

    def campaign(self, day, cid, typ):
        r, c = self.rng, self.people[cid]
        quiet = bool(r.random() < (.25 if day < 90 else .48))
        coached = bool(typ.startswith("scam") and r.random() < .7)
        night = r.random() < (.5 if typ in ("scam_macau", "scam_love") else .18)
        t = day * 1440 + (r.uniform(0, 5) if night else r.uniform(8, 23)) * 60
        pid = int(r.integers(self.customer_count + 1, self.customer_count * 4))
        self.add(max(0, t - r.uniform(3 * 1440, 15 * 1440) if quiet else t - r.uniform(1, 30)),
                 "save", cid, pid=pid)
        self.login(t, cid, new=typ == "account_takeover" and not quiet,
                   password=typ == "account_takeover")
        steps = {"scam_macau": 2, "scam_investment": 7, "scam_job": 9,
                 "scam_love": 6, "account_takeover": 2, "mule": 8, "card_testing": 12}[typ]
        for step in range(steps):
            dt = step * (r.uniform(500, 2300) if typ in ("scam_investment", "scam_job", "scam_love") else r.uniform(.1, 8))
            when = t + dt
            if step and typ in ("scam_investment", "scam_job", "scam_love"):
                self.login(when, cid)
            amount = c.typical * r.lognormal(.5, .85)
            if typ in ("scam_macau", "account_takeover") and not quiet:
                amount *= r.uniform(10, 40)
            if typ in ("scam_investment", "scam_job"):
                amount *= (1.3 if quiet else 1.6) ** step * (.15 if typ == "scam_job" else 1)
            if typ == "card_testing":
                amount = r.lognormal(.8, .7)
            if typ == "mule":
                # Several unrelated sources fund the mule, then it forwards within an hour.
                sender = int(r.integers(1, self.customer_count + 1))
                self.add(max(0, when - r.uniform(1, 55)), "pay", sender, pid=cid,
                         amount=amount, scenario="mule", attack=True, quiet=quiet,
                         coached=False, step=step)
            self.add(when, "pay", cid, pid=pid, amount=amount, scenario=typ,
                     attack=True, quiet=quiet, coached=coached, step=step)

    @staticmethod
    def recent(items, t, window):
        return [x for x in items if t - window <= x[0] < t]

    def run(self):
        self.prepare()
        r = self.rng
        while self.queue:
            t, _, kind, cid, data = heapq.heappop(self.queue)
            c = self.people[cid]
            if kind == "credit":
                c.balance += data["amount"]
            elif kind == "save":
                c.saved.setdefault(data["pid"], t)
            elif kind == "password":
                c.password = t
            elif kind == "login":
                c.login = t
                if data["new"]:
                    # Some genuine customers share a household phone.
                    c.device = int(r.integers(1, self.customer_count + 1)) if r.random() < .15 else self.serial + cid
                    c.device_since = t
                self.device_users[c.device].add(cid)
                c.devices.append((t, c.device))
                for _ in range(r.poisson(.15)):
                    c.failures.append((t,))
                for _ in range(r.poisson(.08)):
                    c.otp.append((t,))
            elif kind == "report":
                c.reports += 1
                self.known.add(data["pid"])
                self.known_victims.add(cid)
                if r.random() < .45:
                    self.watchlist.add(data["pid"])
            elif kind == "pay":
                self.payment(t, cid, c, data)
        return pd.DataFrame(self.rows, columns=COLUMNS)

    def payment(self, t, cid, c, data):
        r = self.rng
        date = START + timedelta(minutes=t)
        pid, typ = data["pid"], data["scenario"]
        attack, quiet = data["attack"], data["quiet"]
        for queue in (c.history, c.failures, c.otp, c.holds, c.devices):
            while queue and queue[0][0] < t - 90 * 1440:
                queue.popleft()
        hist = list(c.history)
        h24 = self.recent(hist, t, 1440)
        h1 = self.recent(hist, t, 60)
        h30 = self.recent(hist, t, 30 * 1440)
        inbound = self.graph[pid]
        while inbound and inbound[0][0] < t - 7 * 1440:
            inbound.popleft()
        ins = list(inbound)
        outs = self.recent(self.outgoing[pid], t, 7 * 1440)
        # Audit every timestamp contributing to an aggregate, including graph edges.
        dependencies = hist + ins + outs + list(c.failures) + list(c.otp) + list(c.holds)
        self.feature_future_reads += sum(x[0] >= t for x in dependencies)
        assert all(x[0] < t for x in dependencies), "Non-past state in features"
        amount = max(.01, float(data["amount"]))
        if r.random() < .32:
            amount = max(1, round(amount / 50)) * 50
        # Every transaction settles from available balance. External credits are explicit.
        if c.balance < c.typical * 2:
            c.balance += c.salary * r.uniform(.2, 1.0)
        amount = round(min(amount, max(.01, c.balance * r.uniform(.70, .99))), 2)
        prior = np.array([x[1] for x in hist])
        median = float(np.median(prior)) if len(prior) else np.nan
        sd = float(prior.std()) if len(prior) > 1 else np.nan
        age = max(0, (t - c.born) / 1440)
        device_age = max(0, (t - c.device_since) / 1440)
        # Continuous overlapping latent circumstances drive telemetry, not output labels.
        pressure = max(0, r.normal(.25, .55))
        unusual = typ != "routine"
        if attack:
            pressure += r.uniform(.15, .55) if quiet else r.uniform(1.3, 2.4)
        elif unusual:
            pressure += r.uniform(.5, 1.5)
        remote = r.random() < (.35 if typ == "account_takeover" and not quiet else .06)
        location = remote or r.random() < .05 or typ == "travel"
        note = str(r.choice(["", "makan", "rent", "family", "polis", "pelaburan", "LHDN", "安全账户", "task"])) if unusual else str(r.choice(["", "food", "rent", "investment", "family", "LHDN"]))
        hits = sum(word in note.lower() for word in KEYWORDS)
        inbound_sum = sum(x[2] for x in ins)
        out_sum = sum(x[1] for x in outs)
        hops = 0 if pid in self.known else (1 if self.edges[pid] & self.known else np.nan)
        baseline = max(.01, median) if np.isfinite(median) else c.typical
        row = [len(self.rows) + 1, cid, pid, date.isoformat(timespec="microseconds"), typ,
            amount, "telegram" if r.random() < .17 else "app",
            str(r.choice(["transfer", "merchant_payment", "qr_payment"], p=[.6, .2, .2])) if typ != "card_testing" else "merchant_payment",
            date.hour, date.weekday(), int(23 <= date.day <= 28), int(festive(date)),
            amount / median if np.isfinite(median) else np.nan,
            (amount - prior.mean()) / sd if sd > 0 else np.nan,
            c.balance, amount / c.balance,
            len(self.recent(hist, t, 5)), len(h1), len(h24), sum(x[1] for x in h1),
            sum(x[1] for x in h24), len({x[2] for x in h24}), len(self.recent(c.failures, t, 1440)),
            max(0, t - c.saved[pid]) if pid in c.saved else np.nan, int(pid not in c.paid_payees),
            max(0, (t - self.accounts[pid]) / 1440), len({x[1] for x in ins if x[0] >= t - 1440}), int(pid in self.watchlist),
            int(device_age < 1), device_age, int(location), float(r.lognormal(6 if location else 1, 1.1)),
            t - c.password if c.password is not None else np.nan, max(0, t - c.login),
            int(remote or typ == "travel" or r.random() < .02), int(r.random() < (.22 if remote else .08)),
            int(r.random() < (.22 if remote else .035)), int(r.random() < .025),
            len({x[1] for x in self.recent(c.devices, t, 7 * 1440)}), len(self.device_users[c.device]),
            float(r.lognormal(3.3 - .6 * pressure, .65)), int(r.random() < min(.8, .22 + .12 * pressure)),
            max(1, int(r.poisson(6 + pressure))), abs(float(r.normal(.2 + .32 * pressure, .5))),
            float(r.lognormal(7.5 - .5 * pressure, .8)), int(r.poisson(.10 + .12 * pressure)),
            int(r.poisson(.3 + .8 * pressure)), len({x[1] for x in ins}),
            min(1, out_sum / inbound_sum) if inbound_sum else np.nan, hops,
            len({x[1] for x in ins if x[1] in self.known_victims}), hits,
            float(r.beta(1 + hits * .4, 5)), int(not note), age,
            t - hist[-1][0] if hist else np.nan,
            float(np.polyfit(np.arange(5), prior[-5:], 1)[0] / baseline) if len(prior) >= 5 else np.nan,
            sum(x[1] == amount for x in h24),
            np.mean([x[3] < 6 for x in h30]) if h30 else np.nan,
            len(self.recent(c.holds, t, 30 * 1440)), c.reports,
            min(5, int(r.poisson(.12 + .6 * pressure))) if r.random() < .15 else np.nan,
            int(r.random() < (.09 if remote else .003)), int(r.random() < min(.5, .03 + pressure * .04)),
            len(self.recent(c.otp, t, 1440))]
        # Observed outcomes arrive after features. Most label noise is unreported fraud.
        reported = attack and r.random() < .40
        false_report = not attack and r.random() < .002
        observed = reported or false_report
        label_type = typ if reported else (str(r.choice(FRAUD_TYPES)) if false_report else "genuine")
        row += [int(observed), label_type, int(observed and data["coached"]),
                amount if observed else 0., "simulator"]
        assert len(row) == 70
        values = dict(zip(INTERNAL_COLUMNS, row))
        self.rows.append([values[name] for name in COLUMNS])
        self.truth.append(bool(attack))
        # Only now mutate settlement/history and schedule later customer reports.
        c.balance = round(c.balance - amount, 2)
        if pid in self.people:
            self.people[pid].balance += amount
        c.history.append((t, amount, pid, date.hour))
        c.paid_payees.add(pid)
        self.graph[pid].append((t, cid, amount))
        self.outgoing[cid].append((t, amount))
        self.edges[cid].add(pid)
        if pressure > 1.6 and r.random() < .15:
            c.holds.append((t,))
        if observed:
            self.add(t + float(r.uniform(2, 35) * 1440), "report", cid, pid=pid)


def auc(y, score):
    """Mann–Whitney ROC-AUC with average ranks for ties."""
    y = np.asarray(y, dtype=int)
    if y.sum() == 0 or y.sum() == len(y):
        return None
    ranks = pd.Series(score).rank(method="average").to_numpy()
    n = y.sum()
    return float((ranks[y == 1].sum() - n * (n + 1) / 2) / (n * (len(y) - n)))


def evaluate(df, days):
    """Train-only preprocessing, class-weighted ridge logistic regression in NumPy."""
    numeric = df[FEATURES].drop(columns=["transaction_type"])
    # Declared category vocabulary avoids learning category availability from test rows.
    encoded = pd.get_dummies(df[["transaction_type"]].astype({
        "transaction_type": pd.CategoricalDtype(["transfer", "merchant_payment", "qr_payment"])}), dtype=float)
    x = pd.concat([numeric, encoded], axis=1).to_numpy(dtype=float)
    day = (pd.to_datetime(df.event_time, utc=True) - pd.Timestamp(START)).dt.total_seconds().to_numpy() / 86400
    split = 120 if days >= 180 else max(1, int(days * 2 / 3))
    train, test = day < split, day >= split
    y = df.is_fraud.to_numpy()
    if not test.any() or len(np.unique(y[train])) < 2 or len(np.unique(y[test])) < 2:
        return {"status": "insufficient rows/classes for temporal baseline"}
    med = np.array([np.median(col[np.isfinite(col)]) if np.isfinite(col).any() else 0
                    for col in x[train].T])
    missing = ~np.isfinite(x)
    x = np.where(missing, med, x)
    low, high = np.quantile(x[train], [.005, .995], axis=0)
    x = np.clip(x, low, high)
    # Signed log limits heavy-tail influence without inspecting target labels.
    x = np.sign(x) * np.log1p(np.abs(x))
    mean, sd = x[train].mean(axis=0), x[train].std(axis=0)
    x = np.column_stack([np.ones(len(x)), (x - mean) / np.maximum(sd, .01), missing.astype(float)])
    xt, yt = x[train], y[train]
    # Deterministic subset keeps this diagnostic practical on a laptop.
    indices = np.random.default_rng(17).choice(len(xt), min(60000, len(xt)), replace=False)
    xt, yt = xt[indices], yt[indices]
    weights = np.where(yt == 1, .5 / yt.mean(), .5 / (1 - yt.mean()))
    coef = np.zeros(xt.shape[1])
    for _ in range(250):
        prob = 1 / (1 + np.exp(-np.clip(xt @ coef, -30, 30)))
        grad = xt.T @ ((prob - yt) * weights) / len(xt)
        grad[1:] += .01 * coef[1:]
        coef -= .08 * grad
    score = x[test] @ coef
    singles = {}
    # Orientation is chosen on training rows only. Report temporal test AUC.
    for feature in FEATURES:
        if feature in ("channel", "transaction_type"):
            for value in sorted(df[feature].unique()):
                s = (df[feature] == value).astype(float).to_numpy()
                direction = 1 if (auc(y[train], s[train]) or .5) >= .5 else -1
                singles[f"{feature}={value}"] = auc(y[test], direction * s[test])
        else:
            s = df[feature].to_numpy(dtype=float)
            finite = np.isfinite(s[train])
            fill = np.median(s[train][finite]) if finite.any() else 0
            s = np.nan_to_num(s, nan=fill)
            direction = 1 if (auc(y[train], s[train]) or .5) >= .5 else -1
            singles[feature] = auc(y[test], direction * s[test])
    best = max(singles, key=lambda name: singles[name] or 0)
    return {"status": "evaluated", "train_days": split, "test_days": days - split,
            "train_rows": int(train.sum()), "test_rows": int(test.sum()),
            "fit_rows": len(xt), "logistic_roc_auc": auc(y[test], score),
            "best_single_feature": best, "best_single_feature_roc_auc": singles[best],
            "single_feature_auc": singles,
            "preprocessing": "Train medians, winsorization, signed log, standardization, missing indicators; fixed categorical vocabulary; balanced ridge logistic, 250 gradient steps."}


def write_dictionary(df, path):
    text = ["# Jaga synthetic v2 data dictionary", "",
        "Offline simulation only. 59 columns: five metadata, 50 event-time features, four labels.",
        "Never train on metadata or labels. `scenario` reveals scripted circumstances and is especially leaky.",
        "Label noise makes scenario and observed fraud_type disagree. Label fields describe observed reports.",
        "Local timezone is UTC+08:00. Money is MYR, rounded to two decimal places.",
        "Every cell is populated. Defaults are fixed constants, never estimated from future rows. Minute intervals are capped at 525600 (one year).",
        "Unknown fraud distance uses 99, meaning no known connection within the implemented one-hop search; it is not a measured 99-hop path.",
        "Calendar starts 2025-01-01. Holiday windows are fixed illustrative 2025 dates; shorter runs may omit Deepavali.",
        "The graph's known-fraud set contains accounts in reports received strictly before this event. Prior reports can themselves be wrong.",
        "", "| Column | Type | Meaning / generation | Default when unavailable |", "|---|---|---|---|"]
    descriptions = {
        "event_id": "Sequential payment row ID after chronological ordering.",
        "customer_id": "Simulated payer ID; persistent persona and history.",
        "payee_id": "Destination account ID; customer or external account.",
        "event_time": "Payment timestamp in ISO 8601 with explicit +08:00 offset.",
        "scenario": "Script metadata, including routine and hard genuine cases. NEVER a model input.",
        "amount": "Lognormal persona-based MYR amount, round-number bias and rare outliers, capped to available balance.",
        "channel": "Observed session channel: app or telegram.",
        "transaction_type": "Payment rail: transfer, merchant_payment or qr_payment.",
        "amount_vs_median_ratio": "Current amount / median of strictly earlier payments within 90 days.",
        "amount_zscore_90d": "Current amount minus past 90-day mean, divided by past population SD; empty with insufficient history.",
        "balance_before": "Available simulated balance before payment, after prior salary/inbound credits and explicit liquidity replenishment.",
        "pct_balance_drained": "Current amount / balance_before, fraction 0–1.",
        "payee_age_minutes": "Minutes since this payer saved the destination; empty if unsaved.",
        "is_first_transfer_to_payee": "Whether no prior payment to this payee exists in the entire simulated history.",
        "payee_account_age_days": "Days since destination creation, from persistent account metadata.",
        "payee_on_watchlist": "Watchlist membership known before payment; stale false entries and delayed, incomplete updates.",
        "is_new_device": "Current device first observed less than one day ago.",
        "device_age_days": "Days since this payer first used current device.",
        "is_new_location": "Current session location differs from usual; travel and telemetry noise overlap attacks.",
        "km_from_usual_location": "Noisy lognormal geolocation distance; occasional incorrect large distances also occur in routine sessions.",
        "minutes_since_password_change": "Minutes since earlier password change, empty if none observed.",
        "minutes_since_login": "Minutes since preceding simulated login.",
        "ip_is_foreign": "Current foreign IP flag from travel/remote session plus geolocation error.",
        "ip_is_hosting_or_vpn": "Current network VPN/hosting observation, including genuine VPN usage.",
        "timezone_mismatch": "Session timezone mismatch with network location, noisy for genuine travellers.",
        "is_emulator_or_headless": "Current client telemetry; genuine automation/testing also occurs.",
        "devices_seen_7d": "Distinct devices in strictly prior seven-day login events.",
        "device_shared_by_customers": "Number of customers already seen using current device at prior logins.",
        "seconds_on_amount_screen": "Current screen dwell seconds; lognormal with latent urgency and large overlap.",
        "account_number_pasted": "Current paste telemetry, sampled with urgency-dependent probability.",
        "session_actions_before_transfer": "Current pre-confirmation action count, Poisson with urgency and noise.",
        "typing_cadence_distance": "Absolute noisy deviation from usual cadence, affected by current urgency.",
        "hesitation_before_confirm_ms": "Current confirmation hesitation milliseconds, noisy lognormal.",
        "hold_to_send_attempts": "Pre-submission UI gesture attempts, Poisson, not fraud-engine outcome.",
        "app_switches_during_transfer": "Pre-submission app switches, Poisson with urgency and overlapping genuine cases.",
        "payee_fan_in_7d": "Distinct earlier senders into destination over seven days.",
        "payee_pass_through_ratio": "Earlier seven-day outflow / inflow at destination, capped at one; empty without inflow.",
        "payee_hops_to_known_fraud": "Zero if destination already reported, one if prior outgoing neighbour is reported; otherwise unknown/empty. Limited one-hop search.",
        "payee_shared_by_victims": "Distinct prior seven-day senders who filed reports before this payment; reports may be wrong or delayed.",
        "note_scam_keyword_hits": "Case-insensitive count of fixed EN/BM/ZH keywords in the current synthetic note; genuine tax/investment notes overlap.",
        "note_similarity_to_known_scams": "Noisy beta-distributed lexical similarity proxy derived from current keyword hits; not an embedding model.",
        "note_is_empty": "Whether current synthetic transfer note is empty.",
        "customer_age_days": "Days since simulated customer creation.",
        "minutes_since_last_txn": "Gap since strictly prior payment, empty on first observed payment.",
        "amount_trend_last_5": "OLS slope of last five earlier amounts divided by prior median; empty before five payments.",
        "same_amount_repeats_24h": "Count of earlier payments in 24h matching current amount exactly in cents.",
        "night_activity_ratio_30d": "Fraction of earlier 30-day payments between midnight and 05:59.",
        "previous_holds_30d": "Count of past simulated screening holds; current outcome excluded.",
        "previous_fraud_reports": "Reports already received for customer, including delayed and erroneous reports.",
        "scam_interview_red_flags": "0–5 prior-to-submission interview response signal, collected on subset of sessions.",
        "customer_said_not_me": "Pre-submission customer signal, noisy and rare; excludes future case replies.",
        "scam_message_checked_recently": "Current session context flag for a pre-submission message check, noisy urgency-dependent Bernoulli.",
        "otp_failures_24h": "Count of strictly earlier simulated failed OTP events within 24h.",
        "is_fraud": "Observed binary label; 60% of true fraud unreported, 0.2% of genuine payments erroneously reported.",
        "fraud_type": "Observed report category; unreported fraud stays genuine, false reports receive a noisy fraud category.",
        "victim_coached": "Observed coaching label for reported scam rows; never an input.",
        "loss_amount": "Observed gross fraud payment amount; zero for observed genuine; excludes recoveries.",
        "label_source": "Constant simulator; all outcomes are synthetic.",
    }
    for name in FEATURES:
        if name.startswith("txn_count_"):
            descriptions[name] = "Count of strictly earlier payer payments in trailing " + name.removeprefix("txn_count_") + "."
        elif name.startswith("txn_amount_"):
            descriptions[name] = "Sum of strictly earlier payer payment amounts in trailing " + name.removeprefix("txn_amount_") + "."
    descriptions.update(hour_of_day="Local current hour 0–23.", day_of_week="Local weekday, Monday=0.",
        is_salary_period="Current calendar day is 23–28 inclusive.",
        is_festive_period="Current date falls in configured CNY, Raya or Deepavali window.",
        distinct_payees_24h="Distinct earlier destinations in trailing 24h.",
        failed_logins_24h="Count of strictly earlier failed login attempts in trailing 24h.",
        payee_inbound_senders_24h="Distinct earlier senders into destination in trailing 24h.")
    assert set(COLUMNS) <= set(descriptions)
    for name in COLUMNS:
        dtype = "string" if df[name].dtype == object else str(df[name].dtype)
        default = DEFAULTS.get(name, "Required identifier, timestamp, scenario or observed label; always generated")
        meaning = descriptions[name].replace("empty", "defaulted").replace("Empty", "Defaulted")
        text.append(f"| {name} | {dtype} | {meaning} | {default} |")
    text += ["", "## Measurement imperfections", "",
        "Non-critical numeric observations receive independent lognormal measurement jitter where appropriate (roughly 30% SD).",
        "No random missingness mask is applied. Unavailable history uses the documented constants. Zero trend denotes insufficient history; zero prior-night ratio denotes no earlier payments.",
        "All feature values use past state plus current event observations. Observed labels may become available weeks later and are attached retrospectively.",
        "For actual training, purge the reporting-delay interval at split boundaries, and evaluate on real analyst labels before deploying."]
    path.write_text("\n".join(text) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--customers", type=int, default=1500)
    parser.add_argument("--days", type=int, default=180)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=Path("datasets/jaga_synthetic_v2.csv"))
    args = parser.parse_args()
    if args.customers < 2 or args.days < 1:
        parser.error("customers must be >=2 and days must be >=1")
    sim = Simulation(args.customers, args.days, args.seed)
    df = sim.run()
    sim.rows.clear()
    if df.empty:
        parser.error("No payments generated; increase customers or days")
    r = np.random.default_rng(args.seed + 1)
    continuous = ["seconds_on_amount_screen", "typing_cadence_distance", "hesitation_before_confirm_ms",
                  "km_from_usual_location", "note_similarity_to_known_scams"]
    for name in continuous:
        df[name] *= r.lognormal(-.045, .30, len(df))
    df.note_similarity_to_known_scams = df.note_similarity_to_known_scams.clip(0, 1)
    for name in FEATURES:
        df[name] = df[name].fillna(DEFAULTS[name])
        if name.endswith("_minutes") or name.startswith("minutes_since_"):
            df[name] = df[name].clip(0, 525600)
    assert not df.isna().any().any(), "Missing cells before serialization"
    assert np.isfinite(df.select_dtypes(include="number").to_numpy()).all()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    for name in ("amount", "balance_before", "loss_amount", "txn_amount_24h"):
        df[name] = df[name].map(lambda value: f"{value:.2f}" if pd.notna(value) else "")
    df.to_csv(args.out, index=False, float_format="%.6f", na_rep="", lineterminator="\n")
    # Diagnose the serialized artifact, including its actual rounding/missing values.
    df = pd.read_csv(args.out)
    assert list(df.columns) == COLUMNS and len(COLUMNS) == 59 and len(FEATURES) == 50
    assert not df.isna().any().any(), "Missing cells after CSV round trip"
    assert not df.select_dtypes(include="object").apply(lambda col: col.str.strip().eq("")).any().any()
    assert df.event_time.is_monotonic_increasing
    assert (df.amount > 0).all() and (df.amount <= df.balance_before + .000001).all()
    report = {"seed": args.seed, "customers": args.customers, "days": args.days,
        "row_count": len(df), "overall_fraud_rate": float(df.is_fraud.mean()),
        "true_scenario_fraud_rate": float(np.mean(sim.truth)),
        "label_disagreement_rate": float(np.mean(np.asarray(sim.truth) != df.is_fraud.to_numpy())),
        "monthly_fraud_rate": df.groupby(df.event_time.str[:7]).is_fraud.mean().to_dict(),
        "rows_per_fraud_type": df.fraud_type.value_counts().to_dict(),
        "missing_percent_per_column": (df.isna().mean() * 100).round(4).to_dict(),
        "empty_cells": int(df.isna().sum().sum()),
        "non_finite_numeric_cells": int((~np.isfinite(df.select_dtypes(include="number"))).sum().sum()),
        "causal_audit": {"future_state_reads": sim.feature_future_reads,
            "method": "Runtime timestamp assertions on every history/graph aggregate; features built before settlement, reports, holds or label assignment. Current session observations known before submission. No future-normalization."},
        "realism": evaluate(df, args.days),
        "limitations": ["Synthetic validation cannot establish real fraud performance.",
            "Frozen 2025 festive windows; 180-day default does not include Deepavali.",
            "Retrospective labels; reporting-delay embargo needed for deployment-style evaluations.",
            "Graph distances are capped at one hop; no invented distances for unknown nodes."]}
    metrics = report["realism"]
    report["realism_targets_met"] = (metrics.get("best_single_feature_roc_auc", 1) < .80
        and .80 <= metrics.get("logistic_roc_auc", 0) <= .92)
    counts = df.fraud_type.value_counts()
    report["dataset_targets"] = {
        "row_count_300k_plus_minus_5_percent": 285000 <= len(df) <= 315000,
        "every_fraud_type_at_least_300": all(counts.get(name, 0) >= 300 for name in FRAUD_TYPES),
        "card_testing_fraction_of_fraud": float(counts.get("card_testing", 0) / max(1, df.is_fraud.sum())),
        "zero_empty_cells": report["empty_cells"] == 0}
    report["csv_sha256"] = hashlib.sha256(args.out.read_bytes()).hexdigest()
    report_path = args.out.with_name(args.out.stem + "_report.json")
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    write_dictionary(df, args.out.with_name(args.out.stem + "_dictionary.md"))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
