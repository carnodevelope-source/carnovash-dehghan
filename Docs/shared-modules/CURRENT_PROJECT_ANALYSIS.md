# Current Project Analysis

## Project Overview

- Frontend stack: `Vue 3`, `Vite`, `Pinia`, `Vue Router`, `Axios`
- Backend stack: `Django 5`, `Django REST Framework`
- Database: MySQL in production, `db.sqlite3` present for local/dev snapshots
- Auth model: cookie-based session auth with CSRF, not JWT
- API namespace: `/api/*`
- Existing shared business domains relevant to extraction:
  - Auth and tenant onboarding: `backend/apps/auth/*`, `frontend/src/views/auth/LoginView.vue`
  - Wallet, payments, software license, feature purchase: `backend/apps/payments/*`, `frontend/src/views/manager/WalletView.vue`, `frontend/src/components/wallet/WalletPanel.vue`
  - Support tickets: `backend/apps/auth/models.py` and support views in `backend/apps/auth/views.py`, `frontend/src/views/support/SupportView.vue`
  - SMS and customer club: `backend/apps/notifications/*`, SMS settings in `backend/apps/services/*`, `frontend/src/views/manager/CustomerClubView.vue`

## Architecture Summary

- Frontend is a single SPA with role-based routes in `frontend/src/router/index.js`.
- Backend is split by business app:
  - `auth`: user, tenant, HQ, support ticket, registration approval
  - `payments`: wallet, deposit, withdrawal, feature purchase, software lock
  - `notifications`: SMS templates, customer groups, SMS send logs, customer import
  - `services`: service catalog and general settings, including SMS templates/provider fields
- Frontend API access is centralized in `frontend/src/services/api.js`.
- Auth state is centralized in `frontend/src/store/auth.store.js`.
- Feature access is resolved server-side via `backend/apps/auth/feature_access.py` and delivered in `/api/auth/me/`.

## Frontend Analysis

### Routing and Guards

- File: `frontend/src/router/index.js`
- Public routes:
  - `/login`
  - `/attendance/:token`
- Protected routes:
  - `/`
  - `/manager/wallet`
  - `/manager/customer-club`
  - `/manager/attendance`
  - `/manager/reports`
  - `/manager/settings`
  - `/support`
  - `/hq`
- Guard behavior:
  - fetches session using `authStore.fetchMe()`
  - redirects HQ users to `/hq`
  - enforces role membership via `meta.roles`
  - enforces software lock via `licenseSafeRoutes`
  - enforces feature gating via `hasAttendanceAccess` and `hasFeatureAccess`

### State Management

- File: `frontend/src/store/auth.store.js`
- Current auth store contains:
  - `user`
  - computed `role`, `platformRole`, `isHq`, `licenseStatus`, `isLicenseLocked`
  - capability helpers such as `canAccessWallet`, `canAccessSupport`
- Reusable extraction candidates:
  - normalized auth store shape
  - session restore on app start
  - logout flow
  - computed permission getters

### API Integration

- File: `frontend/src/services/api.js`
- Existing shared patterns:
  - environment-aware base URL
  - `withCredentials: true`
  - CSRF cookie/header support
  - request/response loading hooks
  - centralized error toast logic
- Reusable extraction candidates:
  - generic API client factory
  - `ensureCsrfToken()`
  - consistent error mapping

## Backend Analysis

### Auth and Tenant Registration

- Main files:
  - `backend/apps/auth/models.py`
  - `backend/apps/auth/views.py`
  - `backend/apps/auth/serializers.py`
  - `backend/apps/auth/urls.py`
- Current capabilities:
  - login by username or phone
  - logout
  - session restore via `/auth/me/`
  - CSRF bootstrap via `/auth/csrf/`
  - tenant registration with support-ticket workflow
  - user management per tenant
  - HQ support workflow
- Important data models:
  - `CarWash`
  - `User`
  - `PendingTenantRegistration`
  - `SupportTicket`
  - `SupportTicketMessage`
  - `SupportTicketAttachment`
- Dependency notes:
  - auth payload depends on feature purchases and license status
  - tenant registration depends on support ticket creation and file attachments

### Wallet, Payment, Subscription-like Locking

- Main files:
  - `backend/apps/payments/models.py`
  - `backend/apps/payments/views.py`
  - `backend/apps/payments/serializers.py`
  - `backend/apps/payments/urls.py`
- Current capabilities:
  - wallet dashboard
  - manual deposit
  - gateway-style deposit request + callback page
  - withdrawal and wallet-to-wallet transfer
  - feature option catalog and purchase flow
  - installment collection
  - software lock status through `license_status_for_tenant()`
- Important data models:
  - `Wallet`
  - `CashflowTransaction`
  - `WalletGatewayRequest`
  - `CarWashFeaturePurchase`
- Financial safety patterns already present:
  - `Decimal` usage
  - `select_for_update()`
  - transaction records for wallet changes
  - due installment processing in backend only
- Extraction candidates:
  - wallet balance service
  - ledger transaction writer
  - software license guard payload
  - feature option catalog abstraction

### Support System

- Backend implementation is inside the `auth` app, not a dedicated `support` app.
- Main endpoints:
  - `GET/POST /api/auth/support/tickets/`
  - `GET /api/auth/support/tickets/<id>/`
  - `POST /api/auth/support/tickets/<id>/messages/`
  - `POST /api/auth/support/tickets/<id>/feedback/`
- Current features:
  - ticket creation
  - threaded replies
  - attachments
  - assignment
  - registration-request ticket reuse
  - customer feedback and quality scoring
- Frontend file:
  - `frontend/src/views/support/SupportView.vue`
- Extraction candidates:
  - ticket summary serializer contract
  - message contract
  - reply flow service
  - customer feedback flow

### SMS and Customer Club

- Main files:
  - `backend/apps/notifications/models.py`
  - `backend/apps/notifications/services.py`
  - `backend/apps/notifications/views.py`
  - `backend/apps/notifications/serializers.py`
  - `backend/apps/notifications/urls.py`
  - `backend/apps/services/models.py`
  - `backend/apps/services/views.py`
- Current capabilities:
  - customer club dashboard
  - smart/manual customer groups
  - SMS template CRUD
  - bulk and simple SMS send
  - SMS wallet charging/debit
  - SMS logs
  - customer Excel import
  - vehicle assignment/release SMS rendering
- SMS provider coupling today:
  - provider request helper exists in `notifications/services.py`
  - settings fields also exist in `GeneralSettings`
  - some code still reads provider credentials from Django settings
- Extraction candidates:
  - provider interface
  - template token renderer
  - campaign batching
  - log payload normalizer

## Module-by-Module Extraction Assessment

### Auth Module

- Current pages:
  - `frontend/src/views/auth/LoginView.vue`
- Current routes:
  - `/login`
- Current APIs:
  - `/api/auth/csrf/`
  - `/api/auth/login/`
  - `/api/auth/logout/`
  - `/api/auth/me/`
  - `/api/auth/tenants/register/`
- Current store/composables:
  - `frontend/src/store/auth.store.js`
- Project-specific couplings:
  - login page branding and copy
  - redirect rules via `defaultRouteByRole`
  - auth payload includes tenant feature and license fields
- Reusable abstraction required:
  - configurable branding
  - configurable login endpoint paths
  - payload normalizer for role, HQ, feature map, license map

### Wallet and Subscription Module

- Current pages/components:
  - `frontend/src/views/manager/WalletView.vue`
  - `frontend/src/components/wallet/WalletPanel.vue`
- Current APIs:
  - `/api/payments/wallet/dashboard/`
  - `/api/payments/wallet/options/`
  - `/api/payments/wallet/deposit/`
  - `/api/payments/wallet/deposit/start/`
  - `/api/payments/wallet/withdraw/`
- Dependencies:
  - `CarWashFeaturePurchase`
  - `Wallet`, `CashflowTransaction`, `WalletGatewayRequest`
  - route guard software lock behavior
- Reusable abstraction required:
  - wallet repository
  - license guard adapter
  - feature catalog config
  - gateway callback adapter

### Support Module

- Current page:
  - `frontend/src/views/support/SupportView.vue`
- Current APIs:
  - `/api/auth/support/tickets/*`
- Dependencies:
  - auth session
  - tenant membership
  - support assignment and HQ workflows
- Reusable abstraction required:
  - ticket API contract
  - category/priority/status config
  - message ownership/presentation helpers

### SMS Module

- Current page:
  - `frontend/src/views/manager/CustomerClubView.vue`
  - SMS settings UI in `frontend/src/views/manager/SettingsView.vue`
- Current APIs:
  - `/api/notifications/customer-club/`
  - `/api/notifications/customer-groups/*`
  - `/api/notifications/sms/templates/*`
  - `/api/notifications/sms/send/`
  - `/api/notifications/sms/simple/`
- Dependencies:
  - SMS wallet
  - general settings
  - vehicle/customer aggregates
- Reusable abstraction required:
  - provider adapter
  - template token registry
  - campaign request builder
  - customer target resolver

## Dependency Matrix

| Module | Frontend Dependencies | Backend Dependencies | Config Dependencies |
|---|---|---|---|
| Auth | `api.js`, `auth.store.js`, router, navigation config | `auth.models`, `auth.serializers`, `auth.views`, session auth | auth endpoints, branding, route redirects |
| Wallet | auth store, wallet views, route guard | `payments.models`, `payments.views`, `auth.models.CarWashFeaturePurchase` | gateway URLs, feature catalog, lock policy |
| Support | auth store, support page, date/error utils | `auth.models.SupportTicket*`, `auth.views` | categories, priorities, SLA copy |
| SMS | auth store, customer club view, settings view | `notifications.*`, `services.GeneralSettings`, `payments.Wallet` | provider credentials, template defaults, segment pricing |

## Risk Notes

- The support module is physically located in the auth app, so extraction should preserve that dependency or split carefully later.
- SMS provider settings are partly duplicated between Django settings and tenant general settings.
- Software subscription logic is implemented as feature purchase logic inside `payments`, not a standalone subscription app.
- Frontend base components such as `BaseInput.vue` and `BaseButton.vue` are placeholders today; reusable UI extraction should not depend on them as-is.

## Practical Extraction Strategy Used For `templates/`

- Do not change active application files.
- Export clean reference modules with:
  - backend service-level code
  - frontend API/store/guard examples
  - config-first contracts
  - integration and customization docs
- Keep module code close to current implementation patterns:
  - session auth
  - CSRF flow
  - Pinia store shape
  - DRF serializer-style payloads
  - `Decimal` for money
