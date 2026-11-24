/**
 * Short names for the API types.
 *
 * `types/api.ts` is GENERATED from the backend's OpenAPI schema (`pnpm gen:api`),
 * never edited by hand. When a backend schema changes, regenerate it and the
 * TypeScript compiler points at every screen that needs updating.
 */

import type { components } from "./api";

type Schemas = components["schemas"];

export type Customer = Schemas["CustomerOut"];
export type Language = NonNullable<Schemas["RegisterRequest"]["preferred_language"]>;
export type Account = Schemas["AccountOut"];
export type Transaction = Schemas["TransactionOut"];
export type TransactionPage = Schemas["TransactionPage"];
export type Inbox = Schemas["InboxOut"];
export type InboxMessage = Schemas["MessageOut"];
export type Payee = Schemas["PayeeOut"];
export type Recipient = Schemas["RecipientOut"];
export type Transfer = Schemas["TransferOut"];
export type Session = Schemas["SessionOut"];
export type Device = Schemas["DeviceOut"];
