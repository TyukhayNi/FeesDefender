# Atlas del CRM sudespacho — inventario de endpoints

> **GENERADO por `scripts.crm_atlas discover` — NO editar a mano.**
> Regenerar: `python -m scripts.crm_atlas discover --phase a`. El `git diff` entre corridas = deriva del tenant.
> Diseño: `docs/superpowers/specs/2026-07-20-crm-atlas-descubrimiento-design.md`.

| Meta | Valor |
|---|---|
| Tenant | `tnm` |
| Generado | (sin sello) |
| Fuente OAS3 | `https://api-crm-commons-pro.sudespacho.biz/api/docs.json` |
| OpenAPI | 3.0.0 · API CRM reference documentation v0.0.1 |
| Auth global | `apiKey` (header `Authorization`) |
| Fase B (esquema por elemento) | ⏳ pendiente |

**548 operaciones** sobre **486 paths declarados** (424 con operación documentada). Por método: DELETE 63 · GET 230 · PATCH 18 · POST 183 · PUT 54.

> ⚠️ 62 paths declarados sin operación documentada en el OpenAPI (ver sección final) — candidatos a sondeo empírico (Fase B).

## Índice por módulo (tag)

| Módulo | Operaciones |
|---|---|
| [Absences](#absences) | 6 |
| [AbsencesConfig](#absencesconfig) | 4 |
| [AccessRegister](#accessregister) | 3 |
| [AccessRegisterForEmployees](#accessregisterforemployees) | 1 |
| [Accounting - Configuration](#accounting---configuration) | 4 |
| [Accounting - Element Accounts](#accounting---element-accounts) | 3 |
| [Accounting - Export Form Lists](#accounting---export-form-lists) | 2 |
| [Accounting Accounts](#accounting-accounts) | 5 |
| [Accounting Export](#accounting-export) | 3 |
| [Activities](#activities) | 6 |
| [ActivityTotals](#activitytotals) | 1 |
| [Articles](#articles) | 9 |
| [Audit Registers](#audit-registers) | 1 |
| [Auth - ApiKey](#auth---apikey) | 1 |
| [Auth - Cache](#auth---cache) | 4 |
| [Auth - Groups](#auth---groups) | 5 |
| [Auth - IP](#auth---ip) | 3 |
| [Auth - Online](#auth---online) | 3 |
| [Auth - Permissions](#auth---permissions) | 4 |
| [Auth - PersonalConfig](#auth---personalconfig) | 3 |
| [Auth - Profile](#auth---profile) | 3 |
| [Auth - Roles](#auth---roles) | 3 |
| [Auth - UserGroups](#auth---usergroups) | 5 |
| [Auth - Users](#auth---users) | 7 |
| [Azure](#azure) | 7 |
| [CalculateAllActivitiesTotals](#calculateallactivitiestotals) | 1 |
| [Calendar](#calendar) | 1 |
| [Certified Mail](#certified-mail) | 2 |
| [Certified Sms](#certified-sms) | 2 |
| [Chat](#chat) | 5 |
| [Client](#client) | 1 |
| [Companies](#companies) | 8 |
| [Concepts](#concepts) | 12 |
| [Concepts of invoices received](#concepts-of-invoices-received) | 5 |
| [Configurations](#configurations) | 7 |
| [Counter Configuration](#counter-configuration) | 6 |
| [Cron](#cron) | 3 |
| [Dashboard](#dashboard) | 1 |
| [Data Migration](#data-migration) | 2 |
| [Documents](#documents) | 8 |
| [Documents Create Multiple](#documents-create-multiple) | 1 |
| [Documents Import](#documents-import) | 5 |
| [Electronic Invoice](#electronic-invoice) | 4 |
| [ElectronicInvoiceConfig](#electronicinvoiceconfig) | 4 |
| [Element Validations](#element-validations) | 3 |
| [ElementRegistries](#elementregistries) | 2 |
| [Elements](#elements) | 2 |
| [Employee Portal](#employee-portal) | 4 |
| [Employees](#employees) | 1 |
| [Expedient](#expedient) | 4 |
| [Exporter/Importer Data](#exporterimporter-data) | 3 |
| [FinanceConcept](#financeconcept) | 3 |
| [Folder Emails Config](#folder-emails-config) | 4 |
| [Folders](#folders) | 7 |
| [Gdocu](#gdocu) | 4 |
| [Google Docs](#google-docs) | 8 |
| [Google Drive](#google-drive) | 7 |
| [Holidays](#holidays) | 8 |
| [Holidays configs](#holidays-configs) | 4 |
| [IberleyAI](#iberleyai) | 4 |
| [Integrations](#integrations) | 1 |
| [Invoice](#invoice) | 15 |
| [Invoices received](#invoices-received) | 1 |
| [Lexnet](#lexnet) | 1 |
| [Lists](#lists) | 4 |
| [Logo](#logo) | 3 |
| [Mail](#mail) | 12 |
| [MailRoundcube](#mailroundcube) | 9 |
| [Make](#make) | 3 |
| [MassiveDelivery](#massivedelivery) | 1 |
| [Meeting Room](#meeting-room) | 3 |
| [Mensatek](#mensatek) | 5 |
| [Menu](#menu) | 1 |
| [Ms OneDrive](#ms-onedrive) | 5 |
| [MyCheckinOption](#mycheckinoption) | 4 |
| [NextFacturae](#nextfacturae) | 2 |
| [Notifications](#notifications) | 3 |
| [Office Configuration](#office-configuration) | 10 |
| [OfficialBook](#officialbook) | 7 |
| [Online Edition](#online-edition) | 6 |
| [Opportunity](#opportunity) | 1 |
| [Panel](#panel) | 8 |
| [Patch](#patch) | 1 |
| [Payment](#payment) | 5 |
| [Payments of invoices received](#payments-of-invoices-received) | 6 |
| [Payroll](#payroll) | 1 |
| [Predefined](#predefined) | 7 |
| [PresignedUrl](#presignedurl) | 2 |
| [Public Holidays](#public-holidays) | 4 |
| [Public Holidays (Multiple)](#public-holidays-multiple) | 1 |
| [Questions](#questions) | 6 |
| [Readiness](#readiness) | 1 |
| [RecalculateAllConcepts](#recalculateallconcepts) | 1 |
| [Recurrence](#recurrence) | 3 |
| [Recurring Payments](#recurring-payments) | 10 |
| [Register](#register) | 11 |
| [RelatedRegister](#relatedregister) | 1 |
| [RelatedRegistries](#relatedregistries) | 1 |
| [RelationsElements](#relationselements) | 3 |
| [Remittances](#remittances) | 5 |
| [Reports](#reports) | 10 |
| [Restore Registers](#restore-registers) | 1 |
| [Series and Counters](#series-and-counters) | 2 |
| [Sms](#sms) | 1 |
| [SudespachoAI](#sudespachoai) | 4 |
| [Tab](#tab) | 2 |
| [Tag](#tag) | 4 |
| [TaxZone](#taxzone) | 2 |
| [Taxes](#taxes) | 9 |
| [Taxes (massive creation)](#taxes-massive-creation) | 1 |
| [Templates](#templates) | 22 |
| [Time Tracking Export Report](#time-tracking-export-report) | 1 |
| [Time Tracking Report](#time-tracking-report) | 1 |
| [Time Worked Report](#time-worked-report) | 1 |
| [TimeTracking](#timetracking) | 4 |
| [TimeTrackingConfig](#timetrackingconfig) | 4 |
| [Upload](#upload) | 3 |
| [VIDSigner](#vidsigner) | 9 |
| [View](#view) | 14 |
| [View Config](#view-config) | 8 |
| [ViewConfig](#viewconfig) | 2 |
| [WhatsApp](#whatsapp) | 7 |
| [Widgets](#widgets) | 5 |
| [WorkGraphics](#workgraphics) | 5 |
| [Zadarma](#zadarma) | 10 |

## Endpoints por módulo

### Absences

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/absences` | Recovers Absences of a given User | `apiKey` | 18 | [↗](https://developers.sudespacho.net/docs/api-crm/get-absences-absences-collection/) |
| `POST` | `/api/absences` | Create absence request | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/post-absences-absences-collection/) |
| `DELETE` | `/api/absences/{id}` | Delete Absences of User | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-absences-absences-item/) |
| `GET` | `/api/absences/{id}` | Recovers absences details | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/get-absences-details-absences-item/) |
| `PATCH` | `/api/absences/{id}` | Update Absences of User | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/update-absences-absences-item/) |
| `GET` | `/api/absences/{id}/chat` | Recovers absences chat | `apiKey` | 17 | [↗](https://developers.sudespacho.net/docs/api-crm/get-absences-chat-list-absences-collection/) |

### AbsencesConfig

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `DELETE` | `/api/absences/config/{element}/{elementId}` | Removes the AbsencesConfig resource. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-absences-config-item/) |
| `GET` | `/api/absences/config/{element}/{elementId}` | Retrieves a AbsencesConfig resource. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/get-absences-config-item/) |
| `POST` | `/api/absences/config/{element}/{elementId}` | Creates a AbsencesConfig resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/create-absences-config-collection/) |
| `PUT` | `/api/absences/config/{element}/{elementId}` | Replaces the AbsencesConfig resource. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/update-absences-config-item/) |

### AccessRegister

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `DELETE` | `/api/access_register/{element}/{id}` | Delete a access register. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-access-registry-access-register-collection/) |
| `POST` | `/api/access_register/{element}/{id}` | Create a new access register. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/post-access-registry-access-register-collection/) |
| `PUT` | `/api/access_register/{element}/{id}` | Update a access register. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/put-access-registry-access-register-collection/) |

### AccessRegisterForEmployees

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/access_register/employees/{element}/{id}` | Create a new access register. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/post-access-registry-access-register-for-employees-collection/) |

### Accounting - Configuration

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/accounting/config/{accountingGroupId}` | Retrieves a Accounting - Configuration resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-accounting-configuration-item/) |
| `POST` | `/api/accounting/config/{accountingGroupId}` | Creates a Accounting - Configuration resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-accounting-configuration-collection/) |
| `PUT` | `/api/accounting/config/{accountingGroupId}` | Replaces the Accounting - Configuration resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/put-accounting-configuration-item/) |
| `GET` | `/api/accounting/config/{accountingGroupId}/legacy` | Retrieves a Accounting - Configuration resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-legacy-accounting-configuration-item/) |

### Accounting - Element Accounts

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/accounting/{element}/` | Retrieves the collection of Accounting - Element Accounts resources. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/get-accounting-element-accounts-collection/) |
| `GET` | `/api/accounting/{element}/{member}` | Retrieves a Accounting - Element Accounts resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-accounting-element-accounts-item/) |
| `POST` | `/api/accounting/{element}/{member}` | Creates a Accounting - Element Accounts resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-accounting-element-accounts-collection/) |

### Accounting - Export Form Lists

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/accounting/export/form-lists/periods` | Retrieves the collection of Accounting - Export Form Lists resources. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/g-et-periods-accounting-export-form-lists-collection/) |
| `GET` | `/api/accounting/export/form-lists/years` | Retrieves the collection of Accounting - Export Form Lists resources. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/g-et-years-accounting-export-form-lists-collection/) |

### Accounting Accounts

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/accountingaccounts` | Get accounting accounts collection. | `apiKey` | 17 | [↗](https://developers.sudespacho.net/docs/api-crm/get-accountingaccounts-accounting-accounts-read-collection/) |
| `POST` | `/api/accountingaccounts` | Create Accounting Accounts | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-accountingaccounts-accounting-accounts-collection/) |
| `DELETE` | `/api/accountingaccounts/{id}` | Delete Accounting Accounts | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-accountingaccounts-accounting-accounts-collection/) |
| `GET` | `/api/accountingaccounts/{id}` | Get Accounting Accounts detail | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-accountingaccounts-detail-accounting-accounts-collection/) |
| `PUT` | `/api/accountingaccounts/{id}` | Update Accounting Accounts | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/put-accountingaccounts-accounting-accounts-collection/) |

### Accounting Export

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/accounting/export/{dataType}/year/{year}/period/{period}/scope/{scope}/check` | Pre descarga | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/check-accounting-export-collection/) |
| `GET` | `/api/accounting/export/{dataType}/year/{year}/period/{period}/scope/{scope}/download` | Descarga contable | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/download-get-accounting-export-collection/) |
| `POST` | `/api/accounting/export/{dataType}/year/{year}/period/{period}/scope/{scope}/download` | Descarga contable | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/download-post-accounting-export-collection/) |

### Activities

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/activities` | Retrieves the collection of Activities resources. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/get-activities-collection/) |
| `POST` | `/api/activities/invoiceable/calculate` | Creates a Activities resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-activities-calculate-activities-collection/) |
| `POST` | `/api/activities/totals/calculate` | Calculates companyTotal & professionalTotal. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-activities-totals-calculate-activity-totals-collection/) |
| `POST` | `/api/activities/totals/calculate/all` | Recalculate totals for all activities between dates. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-activities-totals-calculate-all-calculate-all-activities-totals-collection/) |
| `GET` | `/api/activities/{id}` | Retrieves a Activities resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-activities-item/) |
| `POST` | `/api/activities/{id}` | Create a new Activity from an old one. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/create-from-recurring-activities-item/) |

### ActivityTotals

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/activity_totals/{id}` | Retrieves a ActivityTotals resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-activity-totals-item/) |

### Articles

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/articles` | Get articles collection. | `apiKey` | 17 | [↗](https://developers.sudespacho.net/docs/api-crm/get-articles-articles-read-collection/) |
| `POST` | `/api/articles` | Create article | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-articles-articles-collection/) |
| `GET` | `/api/articles/balances/{element}/{id}` | Get the articles balance | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/get-balances-articles-balances-collection/) |
| `GET` | `/api/articles/default/folders` | Get default folder collection | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/get-default-folder-concept-families-collection/) |
| `POST` | `/api/articles/generate_default_folder` | Generate default folder | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-default-folder-concept-families-collection/) |
| `POST` | `/api/articles/import/activities/{ids}/{related_element}/{related_register_id}` | Import Activities to Articles | `apiKey` | 3 | [↗](https://developers.sudespacho.net/docs/api-crm/post-articles-import-activities-articles-import-activities-item/) |
| `DELETE` | `/api/articles/{id}` | Delete article | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-articles-articles-item/) |
| `GET` | `/api/articles/{id}` | Get article detail | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-article-detail-articles-item/) |
| `PUT` | `/api/articles/{id}` | Update article | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/put-articles-articles-item/) |

### Audit Registers

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/audit/{element}` | List of Registers to be audited!. | `apiKey` | 12 | [↗](https://developers.sudespacho.net/docs/api-crm/audit-registers-audit-registers-collection/) |

### Auth - ApiKey

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/users/api-key/{id}` | Create an ApiKey for a user. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/create-user-api-key-api-key-item/) |

### Auth - Cache

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `DELETE` | `/api/clear/all/cache` | Clear all cache | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-all-cache-remove-cache-collection/) |
| `DELETE` | `/api/clear/all_users/cache` | Clear all users cache | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-all-users-cache-remove-cache-collection/) |
| `DELETE` | `/api/clear/office/cache/{officeName}` | Clear office cache | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-cache-by-office-remove-cache-collection/) |
| `DELETE` | `/api/user/cache/clear/{id}` | Clear the cache of the current user | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-user-cache-remove-cache-collection/) |

### Auth - Groups

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/group` | Get groups collection. | `apiKey` | 17 | [↗](https://developers.sudespacho.net/docs/api-crm/get-all-groups-groups-collection/) |
| `POST` | `/api/group` | Create a group. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-group-group-collection/) |
| `DELETE` | `/api/group/{id}` | Delete a group. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-group-group-collection/) |
| `GET` | `/api/group/{id}` | Get Group detail. | `apiKey` | 3 | [↗](https://developers.sudespacho.net/docs/api-crm/get-group-group-item/) |
| `PUT` | `/api/group/{id}` | Update a group. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/put-group-group-collection/) |

### Auth - IP

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `DELETE` | `/api/auth/ip` | Delete all active authorized IPs. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-authorized-ips-authorized-ips-collection/) |
| `GET` | `/api/auth/ip` | Get the latest active office authorized IP whitelist or empty. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/get-authorized-ips-authorized-ips-collection/) |
| `POST` | `/api/auth/ip` | Create or replace the office authorized IP whitelist. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-authorized-ips-authorized-ips-collection/) |

### Auth - Online

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/online/clients` | Get the list of clients the online user can impersonate. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/get-impersonable-clients-client-current-use-collection/) |
| `GET` | `/api/online/current` | Get the current client being impersonated by the online user. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/get-current-client-use-client-current-use-collection/) |
| `PUT` | `/api/online/{id}` | Select the current client for online user impersonation. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/put-client-current-use-client-current-use-item/) |

### Auth - Permissions

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `PUT` | `/api/permission/reset/role/{roleId}` | Reset permissions for all active, non-deleted users of a role. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/reset-permission-role-permission-collection/) |
| `PUT` | `/api/permission/reset/{userId}` | Reset user permissions. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/reset-permission-permission-collection/) |
| `GET` | `/api/permission/{userId}` | Get Permission for user id. | `apiKey` | 3 | [↗](https://developers.sudespacho.net/docs/api-crm/get-permission-permission-collection/) |
| `PUT` | `/api/permission/{userId}` | Update a permission. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/put-permission-permission-collection/) |

### Auth - PersonalConfig

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `PATCH` | `/api/personal_config/patchDefault/{id}` | Updates the PersonalConfig resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/patch-personal-config-personal-config-item/) |
| `GET` | `/api/personal_config/{id}` | Retrieves the collection of PersonalConfig resources. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-personal-config-personal-config-collection/) |
| `PUT` | `/api/personal_config/{id}` | Replaces the PersonalConfig resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/put-personal-config-personal-config-item/) |

### Auth - Profile

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/avatar` | Upload a avatar. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-avatar-profile-collection/) |
| `GET` | `/api/avatar/invalidate/{id}` | Invalidates cloudfront cache from user | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-file-invalidator-profile-item/) |
| `GET` | `/api/profiles/{id}` | Get user Profile | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-profile-item/) |

### Auth - Roles

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/role/{id}` | Retrieves the collection of Role Permissions. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-role-permissions-roles-collection/) |
| `PUT` | `/api/role/{id}` | Replaces the Roles resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/put-admin-role-roles-collection/) |
| `GET` | `/api/roles` | Get Roles collection. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/get-roles-roles-collection/) |

### Auth - UserGroups

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `PUT` | `/api/user-companies` | Replaces the UserGroups resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/put-user-companies-user-groups-collection/) |
| `GET` | `/api/user-companies/{idUser}` | Get the groups assigned to a user. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-users-companies-user-groups-collection/) |
| `PUT` | `/api/user-groups` | Replaces the UserGroups resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/put-user-groups-user-groups-collection/) |
| `GET` | `/api/user-groups/{idUser}` | Get the groups assigned to a user. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-users-groups-user-groups-collection/) |
| `GET` | `/api/user-related-companies` | Get the user related companies. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/get-user-related-companies-user-groups-collection/) |

### Auth - Users

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/default_users` | Retrieves the collection of User resources. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/get-default-users-user-collection/) |
| `GET` | `/api/user` | Get Users collection. | `apiKey` | 17 | [↗](https://developers.sudespacho.net/docs/api-crm/get-users-users-collection/) |
| `POST` | `/api/user` | Create a user. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-user-user-collection/) |
| `DELETE` | `/api/user/{id}` | Delete a user. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-user-user-item/) |
| `GET` | `/api/user/{id}` | Get User detail. | `apiKey` | 3 | [↗](https://developers.sudespacho.net/docs/api-crm/get-user-user-item/) |
| `PUT` | `/api/user/{id}` | Update a user. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/put-user-user-item/) |
| `GET` | `/api/users/api-key` | Get admin users with non-empty api key. | `apiKey` | 15 | [↗](https://developers.sudespacho.net/docs/api-crm/get-users-with-api-key-users-collection/) |

### Azure

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/entra/callback` | Process the Azure OAuth callback | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/azure-callback-callback-azure-dto-collection/) |
| `POST` | `/api/entra/connect` | Connect Azure for the current office | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/connect-azure-connect-azure-dto-collection/) |
| `POST` | `/api/entra/createFolder` | Create a OneDrive folder for the current office | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/create-azure-folder-create-azure-folder-dto-collection/) |
| `DELETE` | `/api/entra/files/{fileId}/delete` | Delete a file from the office OneDrive folder | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-azure-file-delete-azure-file-dto-item/) |
| `GET` | `/api/entra/files/{fileId}/download` | Download a file from the office OneDrive folder | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/download-azure-file-download-azure-file-dto-item/) |
| `POST` | `/api/entra/revoke` | Revoke Azure connection for the current office | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/revoke-azure-revoke-azure-dto-collection/) |
| `POST` | `/api/entra/uploadFiles` | Upload a file to the office OneDrive folder | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/upload-azure-file-upload-azure-file-dto-collection/) |

### CalculateAllActivitiesTotals

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/calculate_all_activities_totals/{id}` | Retrieves a CalculateAllActivitiesTotals resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-calculate-all-activities-totals-item/) |

### Calendar

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/calendar/notify` | Creates a calendar notification | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-calendar-notification-collection/) |

### Certified Mail

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/certified_mail/get_report` | Retrieves certified mail report. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-report-certified-mail-collection/) |
| `POST` | `/api/certified_mail/send_mail` | Send a certified mail. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/send-mail-certified-mail-collection/) |

### Certified Sms

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/certified_sms/get_report` | Retrieves certified sms report. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-report-certified-sms-collection/) |
| `POST` | `/api/certified_sms/send_sms` | Send a certified sms. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/send-sms-certified-sms-collection/) |

### Chat

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/chat` | Recovers chat | `apiKey` | 18 | [↗](https://developers.sudespacho.net/docs/api-crm/get-chat-list-chat-collection/) |
| `POST` | `/api/chat` | Create chat | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/post-chat-chat-collection/) |
| `DELETE` | `/api/chat/{id}` | Delete chat | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-chat-chat-item/) |
| `GET` | `/api/chat/{id}` | Retrieves a Chat resource. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/get-chat-details-chat-item/) |
| `PUT` | `/api/chat/{id}` | Update chat | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/update-chat-chat-item/) |

### Client

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/client/convert/{id}` | Convert an Preclient to Client | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/convert-client-client-collection/) |

### Companies

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/company` | Creates a Company resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-accounting-groups-company-collection/) |
| `POST` | `/api/company/billing-defaults` | Creates a Company resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/post-accounting-groups-defaults-company-collection/) |
| `GET` | `/api/company/billing-defaults/{id}` | Retrieves a Company resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-accounting-defaults-company-item/) |
| `DELETE` | `/api/company/{id}` | Removes the Company resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-accounting-groups-company-item/) |
| `GET` | `/api/company/{id}` | Retrieves a Company resource. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/get-accounting-groups-company-item/) |
| `PUT` | `/api/company/{id}` | Replaces the Company resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/put-accounting-groups-company-item/) |
| `GET` | `/api/last-used-company` | Retrieves the collection of UseCompany resources. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/get-last-company-use-company-collection/) |
| `PUT` | `/api/use-company/{companyId}` | Replaces the UseCompany resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/put-accounting-groups-use-company-collection/) |

### Concepts

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/concepts` | Creates a Concepts resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-concepts-collection/) |
| `GET` | `/api/concepts/balance/{relatedElement}/{relatedElementId}` | Retrieves the collection of Concepts resources. | `apiKey` | 15 | [↗](https://developers.sudespacho.net/docs/api-crm/get-unbilled-balance-concepts-collection/) |
| `POST` | `/api/concepts/import` | Creates a Concepts resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-convert-activity-into-concept-concepts-collection/) |
| `GET` | `/api/concepts/item/{conceptType}/{id}` | Retrieves a Concepts resource. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/get-concepts-item/) |
| `POST` | `/api/concepts/recalculate/all` | Recalculate periodic concepts by type. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-recalculate-all-concepts-recalculate-all-concepts-collection/) |
| `POST` | `/api/concepts/simulator` | Creates a Concepts resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-simulator-concepts-collection/) |
| `GET` | `/api/concepts/summary/body/{relatedElement}/{relatedElementId}` | Retrieves the collection of Concepts resources. | `apiKey` | 13 | [↗](https://developers.sudespacho.net/docs/api-crm/get-body-account-summary-concepts-collection/) |
| `GET` | `/api/concepts/summary/{relatedElement}/{relatedElementId}` | Retrieves the collection of Concepts resources. | `apiKey` | 15 | [↗](https://developers.sudespacho.net/docs/api-crm/get-account-summary-concepts-collection/) |
| `GET` | `/api/concepts/{conceptType}/default` | Retrieves a Concepts resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-default-concepts-item/) |
| `DELETE` | `/api/concepts/{conceptType}/{id}` | Removes the Concepts resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-concepts-item/) |
| `PATCH` | `/api/concepts/{conceptType}/{id}` | Updates the Concepts resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/patch-concepts-item/) |
| `GET` | `/api/concepts/{relatedElement}/{relatedElementId}` | Retrieves the collection of Concepts resources. | `apiKey` | 15 | [↗](https://developers.sudespacho.net/docs/api-crm/get-concepts-collection/) |

### Concepts of invoices received

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/received-concepts` | Retrieves the collection of Concepts of invoices received resources. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/get-concepts-of-invoices-received-collection/) |
| `POST` | `/api/received-concepts` | Creates a Concepts of invoices received resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-concepts-of-invoices-received-collection/) |
| `DELETE` | `/api/received-concepts/{id}` | Removes the Concepts of invoices received resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-concepts-of-invoices-received-item/) |
| `GET` | `/api/received-concepts/{id}` | Retrieves a Concepts of invoices received resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-concepts-of-invoices-received-item/) |
| `PATCH` | `/api/received-concepts/{id}` | Updates the Concepts of invoices received resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/patch-concepts-of-invoices-received-item/) |

### Configurations

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/config` | Get configurations list | `apiKey` | 17 | [↗](https://developers.sudespacho.net/docs/api-crm/get-list-config-collection/) |
| `POST` | `/api/config` | Create new configurations | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-config-collection/) |
| `GET` | `/api/config/user/{user}` | Get configurations of one user | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-user-config-user-config-item/) |
| `GET` | `/api/config/{element}/configuration/employee` | Get configurations list | `apiKey` | 17 | [↗](https://developers.sudespacho.net/docs/api-crm/get-configuration-employee-config-collection/) |
| `DELETE` | `/api/config/{id}` | Get configurations details | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-config-item/) |
| `GET` | `/api/config/{id}` | Get configurations details | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-details-config-item/) |
| `PUT` | `/api/config/{id}` | Get configurations details | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/update-config-item/) |

### Counter Configuration

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/default_general_counters/{element}` | Creates a Counter Configuration resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/post-default-general-counters-counter-configuration-collection/) |
| `GET` | `/api/general_counters` | Retrieves the collection of Counter Configuration resources. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/get-general-counters-counter-configuration-collection/) |
| `GET` | `/api/general_counters/invoices/sync` | Retrieves the collection of Counter Configuration resources. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/sync-invoices-general-counters-counter-configuration-collection/) |
| `POST` | `/api/general_counters/{element}` | Creates a Counter Configuration resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/post-general-counters-counter-configuration-collection/) |
| `PUT` | `/api/general_counters/{element}` | Replaces the Counter Configuration resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/put-general-counters-counter-configuration-collection/) |
| `DELETE` | `/api/general_counters/{element}/{seriesId}` | Removes the Counter Configuration resource. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-general-counters-counter-configuration-collection/) |

### Cron

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/cron` | Creates a Cron Event | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-cron-collection/) |
| `POST` | `/api/cron/update` | Updates a Cron Event | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/update-cron-collection/) |
| `GET` | `/api/cron/{element}` | Gets events by element | `apiKey` | 3 | [↗](https://developers.sudespacho.net/docs/api-crm/get-cron-item/) |

### Dashboard

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/billing_charts/{id}` | Get user BillingChart | `apiKey` | 6 | [↗](https://developers.sudespacho.net/docs/api-crm/get-billing-chart-item/) |

### Data Migration

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/data_migration/{elementTo}/{elementFrom}` | Migration of data from one item to another. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/post-data-migration-data-migration-collection/) |
| `POST` | `/api/reduced_data_migration` | Migration of data from one item to another. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-data-migration-ids-data-migration-collection/) |

### Documents

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/documents` | Retrieves the collection of Documents resources. | `apiKey` | 18 | [↗](https://developers.sudespacho.net/docs/api-crm/get-list-documents-collection/) |
| `POST` | `/api/documents` | Creates a Documents resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/create-documents-collection/) |
| `GET` | `/api/documents/date-tree` | Retrieves the collection of Documents resources. | `apiKey` | 20 | [↗](https://developers.sudespacho.net/docs/api-crm/get-date-tree-documents-collection/) |
| `DELETE` | `/api/documents/{id}` | Removes the Documents resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-documents-item/) |
| `GET` | `/api/documents/{id}` | Retrieves a Documents resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-details-documents-item/) |
| `PUT` | `/api/documents/{id}` | Replaces the Documents resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/update-documents-item/) |
| `PUT` | `/api/documents/{id}/acceptance` | Replaces the Documents resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/p-ut-documents-item/) |
| `GET` | `/api/documents/{id}/downloadUri` | Retrieves a Documents resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/g-et-documents-item/) |

### Documents Create Multiple

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/documents/multiple` | Creates a Documents Create Multiple resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/create-multiple-documents-create-multiple-collection/) |

### Documents Import

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/documents/convert/doc-to-pdf` | Convert DOC/RTF a PDF | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/document-to-pdf-doc-to-pdf-dto-collection/) |
| `POST` | `/api/documents/massive-document/analyze` | Import multiple documents | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/analyze-massive-document-analyze-dto-collection/) |
| `POST` | `/api/documents/multiple-documents/analyze` | Import multiple documents | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/analyze-multi-documents-analyze-dto-collection/) |
| `POST` | `/api/documents/multiple-documents/import` | Import multiple documents | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/import-multi-documents-import-dto-collection/) |
| `POST` | `/api/documents/single-document/import` | Import multiple documents | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/import-single-document-import-dto-collection/) |

### Electronic Invoice

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/electronic_invoices/create-on-legacy` | Creates a Electronic Invoice resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-invoice-created-on-legacy-electronic-invoice-collection/) |
| `GET` | `/api/electronic_invoices/{id}` | Retrieves a Electronic Invoice resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/electronic-invoice-get-electronic-invoice-item/) |
| `PATCH` | `/api/electronic_invoices/{id}` | Updates the Electronic Invoice resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/electronic-invoice-update-electronic-invoice-item/) |
| `GET` | `/api/electronic_invoices/{userId}/{office}/{id}` | Retrieves a Electronic Invoice resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/electronic-invoice-get-by-user-office-electronic-invoice-item/) |

### ElectronicInvoiceConfig

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/electronic_invoice_configs` | Retrieves the collection of ElectronicInvoiceConfig resources. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/get-electronic-invoice-config-collection/) |
| `GET` | `/api/electronic_invoice_configs/{id}` | Retrieves a ElectronicInvoiceConfig resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-electronic-invoice-config-item/) |
| `GET` | `/api/electronic_invoices_config` | Retrieves a ElectronicInvoiceConfig resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-config-electronic-invoice-config-item/) |
| `POST` | `/api/electronic_invoices_config` | Creates a ElectronicInvoiceConfig resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-electronic-invoice-config-collection/) |

### Element Validations

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/element-validation/check` | Returns if theres any errors on the specified registries | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/check-registers-element-validation-collection/) |
| `POST` | `/api/element-validation/check/{element}/{property}` | Validates element property and updates database register | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/validate-property-element-validation-collection/) |
| `POST` | `/api/element-validation/duplicate/{element}` | Validates duplicate values dynamically | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/validate-duplicate-element-validation-collection/) |

### ElementRegistries

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/element_registries/summary/{element}` | Retrieves the summation collection of Register. | `apiKey` | 20 | [↗](https://developers.sudespacho.net/docs/api-crm/get-summation-element-registries-summation-element-registries-collection/) |
| `GET` | `/api/element_registries/{element}` | Retrieves the collection of Register. | `apiKey` | 22 | [↗](https://developers.sudespacho.net/docs/api-crm/get-resource-registries-element-registries-collection/) |

### Elements

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/elements` | Get elements collection | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-file-template-elements-collection/) |
| `POST` | `/api/elements/count_related` | Count elements related to other element | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/count-related-count-related-elements-collection/) |

### Employee Portal

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/employee_portal` | Integrate Employee Portal office | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-integrate-employee-portal-employee-portal-integration-collection/) |
| `GET` | `/api/employee_portal/autologin` | Employee Portal autologin | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/get-autologin-employee-portal-integration-collection/) |
| `POST` | `/api/employee_portal/user` | Integrate Employee Portal user | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-integrate-employee-portal-user-employee-portal-integration-collection/) |
| `GET` | `/api/employee_portal/{type}` | Read Employee Portal office or user integration | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-integration-employee-portal-integration-collection/) |

### Employees

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/employees/info-by-user/{userId}` |  | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-user-config-employee-info-item/) |

### Expedient

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/expedient/convert/{id}` | Convert an expedient "ExtraJudicial" to "Judicial" | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/convert-judicial-expedient-item/) |
| `POST` | `/api/export/complete/{element}` | Export complete elements data by ids. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/post-complete-export-data-exporter-collection/) |
| `PUT` | `/api/{element}/{id}/sync-balance` | Synchronize balances for extrajudicial or judicial expedients | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/sync-balance-expedient-balance-item/) |
| `POST` | `/api/{element}/{id}/totals` | Preview totals for extrajudicial or judicial expedients | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/preview-totals-expedient-balance-item/) |

### Exporter/Importer Data

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/download_file_template/{type}/{element}` | Download file templates for importing data | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/get-file-template-file-templates-collection/) |
| `GET` | `/api/export/{type}/{element}` | Export data to csv. | `apiKey` | 19 | [↗](https://developers.sudespacho.net/docs/api-crm/get-export-data-exporter-collection/) |
| `POST` | `/api/import/{fileType}/{element}/{fileIdentifier}` | Import data to csv. | `apiKey` | 3 | [↗](https://developers.sudespacho.net/docs/api-crm/post-import-data-importer-collection/) |

### FinanceConcept

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/finance-concepts` | Creates a FinanceConcept resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-finance-concept-collection/) |
| `DELETE` | `/api/finance-concepts/{id}` | Removes the FinanceConcept resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-finance-concept-item/) |
| `PATCH` | `/api/finance-concepts/{id}` | Updates the FinanceConcept resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/patch-finance-concept-item/) |

### Folder Emails Config

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `DELETE` | `/api/folders/{carpetaId}/config/emails` | Removes the Folder Emails Config resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-folder-emails-config-item/) |
| `GET` | `/api/folders/{carpetaId}/config/emails` | Retrieves a Folder Emails Config resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-folder-emails-config-item/) |
| `POST` | `/api/folders/{carpetaId}/config/emails` | Creates a Folder Emails Config resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/create-folder-emails-config-collection/) |
| `PUT` | `/api/folders/{carpetaId}/config/emails` | Replaces the Folder Emails Config resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/update-folder-emails-config-item/) |

### Folders

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/all_folders/{idUser}` | Get the groups assigned to a user. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-all-folders-with-access-folders-permissions-collection/) |
| `GET` | `/api/folders/all/{element}/{userId}` | Get all folders collection. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/get-all-folders-folders-collection/) |
| `PUT` | `/api/folders/permissions/{userId}` | Update a access folders. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/put-access-folders-folders-permissions-collection/) |
| `GET` | `/api/folders/{element}/{parent}` | Get folders collection. | `apiKey` | 4 | [↗](https://developers.sudespacho.net/docs/api-crm/get-folders-folders-collection/) |
| `POST` | `/api/folders/{element}/{parent}` | Create folder | `apiKey` | 4 | [↗](https://developers.sudespacho.net/docs/api-crm/post-folder-create-folders-collection/) |
| `DELETE` | `/api/folders/{id}` | Update folder | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-folder-delete-folders-collection/) |
| `PUT` | `/api/folders/{id}` | Update folder | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/put-folder-edit-folders-collection/) |

### Gdocu

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/documents/{id}/summary` | Summarizes one file using AI | `apiKey` | 19 | [↗](https://developers.sudespacho.net/docs/api-crm/get-document-summary-documents-collection/) |
| `GET` | `/api/documents/{id}/zip/files` | Returns all files compressed in a zip | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-archive-files-documents-item/) |
| `GET` | `/api/files/{id}/versions` | Get file versions | `apiKey` | 3 | [↗](https://developers.sudespacho.net/docs/api-crm/get-versions-file-item/) |
| `GET` | `/api/files/{id}/versions/{version}` | Get a presigned url to download a file version | `apiKey` | 3 | [↗](https://developers.sudespacho.net/docs/api-crm/get-presigned-url-file-item/) |

### Google Docs

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/gdocs` | Creates a Google Docs resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/p-ost-google-docs-collection/) |
| `GET` | `/api/gdocs/access_token` | Retrieves the collection of Google Docs resources. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/g-et-access-token-google-docs-collection/) |
| `GET` | `/api/gdocs/authorization_url` | Retrieves the collection of Google Docs resources. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/g-et-auth-url-google-docs-collection/) |
| `GET` | `/api/gdocs/export/{id}` | Retrieves a Google Docs resource. | `apiKey` | 4 | [↗](https://developers.sudespacho.net/docs/api-crm/g-et-export-google-docs-item/) |
| `GET` | `/api/gdocs/redirect` | Retrieves the collection of Google Docs resources. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/g-et-redirect-google-docs-collection/) |
| `DELETE` | `/api/gdocs/stored_access_token` | Removes the Google Docs resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/d-elete-stored-access-token-google-docs-collection/) |
| `GET` | `/api/gdocs/stored_access_token` | Retrieves the collection of Google Docs resources. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/g-et-stored-access-token-google-docs-collection/) |
| `GET` | `/api/gdocs/{id}` | Retrieves a Google Docs resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/g-et-google-docs-item/) |

### Google Drive

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/drive/callback` | Process the Google Drive OAuth callback | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/drive-callback-callback-drive-dto-collection/) |
| `POST` | `/api/drive/connect` | Connect Google Drive for the current office | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/connect-drive-connect-drive-dto-collection/) |
| `POST` | `/api/drive/createFolder` | Create a Google Drive folder for the current office | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/create-drive-folder-create-drive-folder-dto-collection/) |
| `DELETE` | `/api/drive/files/{fileId}/delete` | Delete a file from the office Drive folder | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-drive-file-delete-drive-file-dto-item/) |
| `GET` | `/api/drive/files/{fileId}/download` | Download a file from the office Drive folder | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/download-drive-file-download-drive-file-dto-item/) |
| `POST` | `/api/drive/revoke` | Revoke Google Drive connection for the current office | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/revoke-drive-revoke-drive-dto-collection/) |
| `POST` | `/api/drive/uploadFiles` | Upload a file to the office Drive folder | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/upload-drive-file-upload-drive-file-dto-collection/) |

### Holidays

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/holidays` | Recovers Holidays of a given User | `apiKey` | 18 | [↗](https://developers.sudespacho.net/docs/api-crm/get-holidays-holidays-collection/) |
| `POST` | `/api/holidays` | Create holiday request. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/post-holidays-holidays-collection/) |
| `GET` | `/api/holidays/report/employee/{employeeId}` | Report of holidays by employee | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-user-config-holidays-report-item/) |
| `GET` | `/api/holidays/validation` | Report of holidays by employee | `apiKey` | 21 | [↗](https://developers.sudespacho.net/docs/api-crm/validate-holidays-collection/) |
| `DELETE` | `/api/holidays/{id}` | Delete Holidays of User | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-holidays-holidays-item/) |
| `GET` | `/api/holidays/{id}` | Recovers holidays details | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/get-holidays-details-holidays-item/) |
| `PATCH` | `/api/holidays/{id}` | Update Holidays of User | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/update-holidays-holidays-item/) |
| `GET` | `/api/holidays/{id}/chat` | Recovers holidays chat | `apiKey` | 17 | [↗](https://developers.sudespacho.net/docs/api-crm/get-holidays-chat-list-holidays-collection/) |

### Holidays configs

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `DELETE` | `/api/holidays/config/{element}/{elementId}` | Delete holidays config | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-holidays-config-item/) |
| `GET` | `/api/holidays/config/{element}/{elementId}` | Get holidays config details | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/get-details-holidays-config-item/) |
| `POST` | `/api/holidays/config/{element}/{elementId}` | Create new holidays config | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/create-holidays-config-collection/) |
| `PUT` | `/api/holidays/config/{element}/{elementId}` | Update holidays config | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/update-holidays-config-item/) |

### IberleyAI

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/iberleyai/credentials/{id}` | Recovers IberleyAI login credentials | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-login-data-iberley-ai-collection/) |
| `GET` | `/api/iberleyai/login/{id}` | Recovers IberleyAI login tokens | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-login-iberley-ai-collection/) |
| `DELETE` | `/api/iberleyai/{id}` | Deletes IberleyAI configuration | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-config-iberley-ai-collection/) |
| `POST` | `/api/iberleyai/{id}` | Create IberleyAI request. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/post-integration-iberley-ai-collection/) |

### Integrations

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/integrations/{id}` | Get Integrations. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-panel-integrations-item/) |

### Invoice

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/invoices` | Creates a Invoice resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-invoice-collection/) |
| `POST` | `/api/invoices/amend` | Creates a Invoice resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-amend-invoice-collection/) |
| `POST` | `/api/invoices/amend/simulator` | Creates a Invoice resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-amend-simulator-invoice-collection/) |
| `POST` | `/api/invoices/cancel` | Creates a Invoice resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-invoice-cancel-invoice-collection/) |
| `POST` | `/api/invoices/convert` | Convert a Proforma Invoice to a Normal Invoice and delete the original Proforma Invoice. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-convert-invoice-collection/) |
| `POST` | `/api/invoices/copy` | Create a Normal Invoice from a Proforma Invoice, retaining the original Proforma Invoice. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-copy-invoice-collection/) |
| `POST` | `/api/invoices/duplicate` | Creates a Invoice resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-duplicate-invoice-collection/) |
| `POST` | `/api/invoices/fix` | Creates a Invoice resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-invoice-fix-invoice-collection/) |
| `POST` | `/api/invoices/mass/retrieve` | Creates a Invoice resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-mass-retrieve-invoice-collection/) |
| `POST` | `/api/invoices/preview` | Creates a Invoice resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-preview-invoice-collection/) |
| `POST` | `/api/invoices/recalculate` | Recalculate invoice totals and status based on related concepts and payments. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-invoice-recalculate-invoice-collection/) |
| `POST` | `/api/invoices/resend` | Creates a Invoice resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-invoice-resend-next-facturae-invoice-collection/) |
| `PATCH` | `/api/invoices/{element}/{id}` | Updates the Invoice resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/patch-invoice-item/) |
| `DELETE` | `/api/invoices/{id}` | Removes the Invoice resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-invoice-item/) |
| `GET` | `/api/invoices/{id}` | Retrieves a Invoice resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/retrieve-invoice-item/) |

### Invoices received

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/received-invoices/duplicate` | Creates a Invoices received resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-duplicate-invoices-received-collection/) |

### Lexnet

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/lexnet/import` | Zip file import | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-lexnet-lexnet-collection/) |

### Lists

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/list/{element}/{field}` | Adding items to a List. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/post-list-lists-collection/) |
| `DELETE` | `/api/list/{element}/{field}/{ids}` | Remove items to a List. | `apiKey` | 3 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-list-lists-collection/) |
| `PUT` | `/api/list/{element}/{field}/{listId}` | Update the label of an element in the list. | `apiKey` | 3 | [↗](https://developers.sudespacho.net/docs/api-crm/update-list-lists-collection/) |
| `PUT` | `/api/lists/all/{element}/{field}` | Update all items in a List. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/update-all-list-lists-collection/) |

### Logo

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/logo/upload_logo/{type}` | Uploaded logo. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/post-logo-logo-collection/) |
| `DELETE` | `/api/logo/{type}` | Get logo url. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-logo-logo-collection/) |
| `GET` | `/api/logo/{type}` | Get logo url. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/get-logo-logo-collection/) |

### Mail

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/mail/accounts_links/{id}` | Retrieves a AccountLinks resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-account-links-item/) |
| `GET` | `/api/mail/attach/{id}` | Retrieves a DownloadAttachment resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-download-attachment-item/) |
| `POST` | `/api/mail/autoassign` | Queue asynchronous autoassignment for Roundcube mails. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-autoassign-mail-auto-assign-collection/) |
| `GET` | `/api/mail/autoassign/config` | Get auto-assign configuration and valid elements. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/get-config-mail-auto-assign-collection/) |
| `POST` | `/api/mail/autoassign/config` | Create or update auto-assign configuration. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-config-mail-auto-assign-collection/) |
| `GET` | `/api/mail/migrate/legacy` | Fix emails permissions from legacy creating a permission for user and group using creator as reference | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/migrate-legacy-migrate-from-legacy-collection/) |
| `GET` | `/api/mail/permissions/{id}` | Retrieves a MailPermissions resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-mail-permissions-item/) |
| `POST` | `/api/mail/recipients` | Creates a MailRecipients resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/get-mail-recipients-mail-recipients-collection/) |
| `GET` | `/api/mail/recipients/all` | Retrieves the collection of MailRecipients resources. | `apiKey` | 3 | [↗](https://developers.sudespacho.net/docs/api-crm/get-all-mail-recipients-mail-recipients-collection/) |
| `GET` | `/api/mail/{idMail}/tracking/{relatedElement}/{relatedId}` | Retrieves the collection of MailRelatedTracking resources. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/get-related-tracking-mail-related-tracking-collection/) |
| `GET` | `/api/mail/{id}` | Retrieves a Mail resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-mail-item/) |
| `GET` | `/api/mail/{id}/{relatedElement}/{relatedElementId}` | Retrieves a MailByRelatedElement resource. | `apiKey` | 3 | [↗](https://developers.sudespacho.net/docs/api-crm/get-element-relation-mail-by-related-element-item/) |

### MailRoundcube

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/mail/attachments` | Creates a MailRoundcube resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-has-attachments-mail-roundcube-collection/) |
| `POST` | `/api/mail/findAssigned` | Creates a MailRoundcube resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/get-assigned-mails-mail-roundcube-collection/) |
| `GET` | `/api/mail/findRelations/{uid}` | Retrieves the collection of MailRoundcube resources. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/get-mail-relations-mail-roundcube-collection/) |
| `POST` | `/api/mail/relate/attachments` | Creates a MailRoundcube resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-relate-attachments-mail-roundcube-collection/) |
| `POST` | `/api/mail/relate/selected` | Creates a MailRoundcube resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-relate-selected-registers-mail-roundcube-collection/) |
| `DELETE` | `/api/mail_roundcubes/{id}` | Removes the MailRoundcube resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-mail-roundcube-item/) |
| `GET` | `/api/mail_roundcubes/{id}` | Retrieves a MailRoundcube resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-mail-roundcube-item/) |
| `PATCH` | `/api/mail_roundcubes/{id}` | Updates the MailRoundcube resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/patch-mail-roundcube-item/) |
| `PUT` | `/api/mail_roundcubes/{id}` | Replaces the MailRoundcube resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/put-mail-roundcube-item/) |

### Make

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `DELETE` | `/api/make` | Deletes Make integration. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-integration-make-integration-dto-collection/) |
| `GET` | `/api/make` | Gets Make integration. | `apiKey` | 15 | [↗](https://developers.sudespacho.net/docs/api-crm/get-integration-make-integration-dto-collection/) |
| `POST` | `/api/make` | Creates Make integration. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/create-integration-make-integration-dto-collection/) |

### MassiveDelivery

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/massive-delivery/send` | Returns if theres any errors on the specified registries | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/send-massive-massive-delivery-collection/) |

### Meeting Room

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/calendar/meetingroom` | Returns meeting room status for all avaliable users | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/get-meeting-room-dto-collection/) |
| `POST` | `/api/calendar/meetingroom` | Creates or updates meeting room status for provied user | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-meeting-room-dto-collection/) |
| `DELETE` | `/api/calendar/meetingroom/{id}` | Deletes meeting room for provided user | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-meeting-room-dto-item/) |

### Mensatek

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `DELETE` | `/api/mensatek` | Deletes Mensatek integration. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-integration-mensatek-collection/) |
| `GET` | `/api/mensatek` | Retrieves Mensatek integration. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/get-integration-mensatek-collection/) |
| `POST` | `/api/mensatek` | Creates Mensatek integration. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/create-integration-mensatek-collection/) |
| `GET` | `/api/mensatek/services` | Retrieves Mensatek services. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/get-services-mensatek-collection/) |
| `POST` | `/api/mensatek/services` | Configurates Mensatek services. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/services-mensatek-collection/) |

### Menu

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/menus/{id}` | Get user Menu | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/get-menu-item/) |

### Ms OneDrive

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/msonedrive/access_token` | Retrieves the collection of Ms OneDrive resources. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/g-et-access-token-ms-one-drive-collection/) |
| `GET` | `/api/msonedrive/authorization_url` | Retrieves the collection of Ms OneDrive resources. | `apiKey` | 3 | [↗](https://developers.sudespacho.net/docs/api-crm/g-et-auth-url-ms-one-drive-collection/) |
| `GET` | `/api/msonedrive/redirect` | Retrieves the collection of Ms OneDrive resources. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/g-et-redirect-ms-one-drive-collection/) |
| `DELETE` | `/api/msonedrive/stored_access_token` | Removes the Ms OneDrive resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/d-elete-stored-access-token-ms-one-drive-collection/) |
| `GET` | `/api/msonedrive/stored_access_token` | Retrieves the collection of Ms OneDrive resources. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/g-et-stored-access-token-ms-one-drive-collection/) |

### MyCheckinOption

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `DELETE` | `/api/timetracking/config/my_checkin_option/{idUser}` | Delete resource | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-mco-my-checkin-option-item/) |
| `GET` | `/api/timetracking/config/my_checkin_option/{idUser}` | Get resource | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-mco-my-checkin-option-item/) |
| `POST` | `/api/timetracking/config/my_checkin_option/{idUser}` | Create resource | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/create-mco-my-checkin-option-collection/) |
| `PUT` | `/api/timetracking/config/my_checkin_option/{idUser}` | Update resource | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/update-mco-my-checkin-option-item/) |

### NextFacturae

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/nextfacturae` | Creates NextFacturae integration. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/create-integration-next-facturae-collection/) |
| `POST` | `/api/nextfacturae/validate_nif` | Validates nif using NextFacturae. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/validate-nif-next-facturae-collection/) |

### Notifications

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/notifications/events/read` | Mark Event As Read | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-event-read-status-notifications-collection/) |
| `GET` | `/api/notifications/{id}` | Get Notifications. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-panel-notifications-item/) |
| `PUT` | `/api/notifications/{id}` | Put Notifications | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/post-notifications-notifications-collection/) |

### Office Configuration

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/configuration` | Get Configuration. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/get-configuration-office-configuration-collection/) |
| `PUT` | `/api/configuration` | Put Configuration | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/put-configuration-office-configuration-collection/) |
| `GET` | `/api/configuration/configurated` | Get Configured. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/get-configured-office-configuration-collection/) |
| `PUT` | `/api/configuration/configurated` | Put Configurated | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/put-configurated-office-configuration-collection/) |
| `POST` | `/api/configuration/office/install` | Create a new Office | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-install-office-office-service-collection/) |
| `PUT` | `/api/configuration/office/updateVersion` | Update an existing office | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/office-service-collection/) |
| `GET` | `/api/configuration/service_status` | Get Service Status. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/get-service-status-office-service-status-collection/) |
| `PUT` | `/api/configuration/service_status` | Put Service Status | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/put-service-status-office-service-status-collection/) |
| `GET` | `/api/configuration/service_status/all/{page}` | Get Service All Status. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-all-service-status-office-service-status-collection/) |
| `GET` | `/api/configuration/unauthorized/{office}` | Get Configuration Unauthorized. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-configuration-unauthorized-office-unauthorized-configuration-collection/) |

### OfficialBook

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/official-book/aeat/{id}/{configId}` | Retrieve a AEAT Txt file for official book given | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/export-official-book-to-aeat-file-official-book-item/) |
| `POST` | `/api/official-book/export/{type}/{id}` | Retrieve a CSV/XLSX/TXT file for an official book | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/retrieve-accounting-list-csv-official-book-item/) |
| `GET` | `/api/official-book/properties/{id}` | Retrieve a list of properties for the given official book | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/retrieve-accounting-list-properties-official-book-item/) |
| `POST` | `/api/official-book/report/{id}` | Retrieve a report for given accounting list | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/retrieve-accounting-list-official-book-item/) |
| `POST` | `/api/official-book/report/{id}/detail` | Retrieve a report for given accounting list | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/retrieve-official-book-detail-official-book-item/) |
| `POST` | `/api/official-book/totals/{id}` | Retrieve a total's report for given official book | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/retrieve-accounting-list-totals-official-book-item/) |
| `GET` | `/api/official-book/zone/{id}` | Retrieve a list of existing types of Official Books | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/retrieve-official-book-types-official-book-item/) |

### Online Edition

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/online-edition/finish/process` | Sync file | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-sync-file-online-edition-collection/) |
| `POST` | `/api/online-edition/init/process` | Move file | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-mount-file-online-edition-collection/) |
| `DELETE` | `/api/online-edition/online editions/{id}` | Removes the Online Edition resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-online-edition-item/) |
| `GET` | `/api/online-edition/online editions/{id}` | Retrieves a Online Edition resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-online-edition-item/) |
| `PATCH` | `/api/online-edition/online editions/{id}` | Updates the Online Edition resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/patch-online-edition-item/) |
| `PUT` | `/api/online-edition/online editions/{id}` | Replaces the Online Edition resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/put-online-edition-item/) |

### Opportunity

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/opportunity/{parentId}/{elementChild}` | Creates a new element from an opportunity | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/get-data-merge-opportunity-dto-collection/) |

### Panel

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/panel` | Create a Panel. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-panel-panel-collection/) |
| `GET` | `/api/panel/selected` | Get the selected user panel. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/get-default-user-panel-panel-collection/) |
| `PUT` | `/api/panel/selected/{id}` | Update the selected user panel. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/put-default-user-panel-panel-collection/) |
| `DELETE` | `/api/panel/{id}` | Remove panel. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-panel-panel-collection/) |
| `GET` | `/api/panel/{id}` | Get Panel detail. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-panel-panel-collection/) |
| `PUT` | `/api/panel/{id}` | Update a panel. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/put-panel-panel-collection/) |
| `GET` | `/api/panels` | Get Panel collection. | `apiKey` | 17 | [↗](https://developers.sudespacho.net/docs/api-crm/get-panels-panels-collection/) |
| `GET` | `/api/panels/all` | Get Panel collection. | `apiKey` | 17 | [↗](https://developers.sudespacho.net/docs/api-crm/get-panels-all-panels-collection/) |

### Patch

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/patch/{patchName}/{office}` | Runs a patch | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/run-patch-patch-dto-collection/) |

### Payment

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/invoices/{invoiceType}/{invoiceId}/due-amount` | Retrieves a Payment resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-due-amount-payment-item/) |
| `POST` | `/api/payments` | Creates a Payment resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-payment-collection/) |
| `PUT` | `/api/payments/mass/{ids}` | Replaces the Payment resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/put-mass-payment-collection/) |
| `DELETE` | `/api/payments/{id}` | Removes the Payment resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-payment-item/) |
| `PATCH` | `/api/payments/{id}` | Updates the Payment resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/patch-payment-item/) |

### Payments of invoices received

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/received-payments` | Retrieves the collection of Payments of invoices received resources. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/get-payments-of-invoices-received-collection/) |
| `POST` | `/api/received-payments` | Creates a Payments of invoices received resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-payments-of-invoices-received-collection/) |
| `DELETE` | `/api/received-payments/{id}` | Removes the Payments of invoices received resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-payments-of-invoices-received-item/) |
| `GET` | `/api/received-payments/{id}` | Retrieves a Payments of invoices received resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-payments-of-invoices-received-item/) |
| `PATCH` | `/api/received-payments/{id}` | Updates the Payments of invoices received resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/patch-payments-of-invoices-received-item/) |
| `GET` | `/api/received-payments/{invoiceId}/due-amount` | Retrieves a Payments of invoices received resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-due-amount-payments-of-invoices-received-item/) |

### Payroll

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/payroll/preview` | Creates a Payroll resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-priview-payroll-collection/) |

### Predefined

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/predefined` | Get predefined collection. | `apiKey` | 18 | [↗](https://developers.sudespacho.net/docs/api-crm/get-predefined-predefined-collection/) |
| `GET` | `/api/predefined/folder/{folder_id}/{element}/{related_element}/{related_register_id}` | Use a predefined Folder. | `apiKey` | 4 | [↗](https://developers.sudespacho.net/docs/api-crm/get-predefined-use-folder-predefined-use-folder-collection/) |
| `GET` | `/api/predefined/import/{ids}` | Use a predefined. | `apiKey` | 3 | [↗](https://developers.sudespacho.net/docs/api-crm/get-predefined-use-predefined-use-collection/) |
| `POST` | `/api/predefined/{element}` | Create predefined. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/post-predefined-predefined-collection/) |
| `DELETE` | `/api/predefined/{element}/{ids}` | Remove predefined. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-predefined-predefined-collection/) |
| `PUT` | `/api/predefined/{element}/{id}` | Update predefined. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/put-predefined-predefined-collection/) |
| `GET` | `/api/predefined/{id}` | Get predefined detail. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-predefined-predefined-detail-collection/) |

### PresignedUrl

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/documents/presigned_urls/{service}/download/{documentId}` | Retrieves a PresignedUrl resource. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/get-one-down-presigned-url-item/) |
| `GET` | `/api/documents/presigned_urls/{service}/upload/{numberOfUrls}` | Retrieves the collection of PresignedUrl resources. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/get-presigned-url-collection/) |

### Public Holidays

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/public-holidays` | Creates a Public Holidays resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/create-public-holidays-collection/) |
| `DELETE` | `/api/public-holidays/{id}` | Removes the Public Holidays resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-public-holidays-item/) |
| `GET` | `/api/public-holidays/{id}` | Retrieves a Public Holidays resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-public-holidays-item/) |
| `PUT` | `/api/public-holidays/{id}` | Replaces the Public Holidays resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/update-public-holidays-item/) |

### Public Holidays (Multiple)

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/public-holidays/multiple` | Creates a Public Holidays (Multiple) resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/create-public-holidays-multiple-collection/) |

### Questions

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/questions` | Recovers questions | `apiKey` | 18 | [↗](https://developers.sudespacho.net/docs/api-crm/get-questions-list-question-collection/) |
| `POST` | `/api/questions` | Create question | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/post-questions-question-collection/) |
| `DELETE` | `/api/questions/{id}` | Delete question | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-questions-question-item/) |
| `GET` | `/api/questions/{id}` | Retrieves a Question resource. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/get-questions-details-question-item/) |
| `PUT` | `/api/questions/{id}` | Update question | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/update-questions-question-item/) |
| `GET` | `/api/questions/{id}/chat` | Recovers questions chat | `apiKey` | 17 | [↗](https://developers.sudespacho.net/docs/api-crm/get-questions-chat-list-question-collection/) |

### Readiness

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/health` | Health check. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/readiness-readiness-collection/) |

### RecalculateAllConcepts

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/recalculate_all_concepts/{id}` | Retrieves a RecalculateAllConcepts resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-recalculate-all-concepts-item/) |

### Recurrence

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/recurrence/calculate` | Creates and returns rrule. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/calculate-recurrence-rrule-dto-collection/) |
| `POST` | `/api/recurrence/reverse` | Reverses rrule. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/reverse-recurrence-rrule-dto-collection/) |
| `POST` | `/api/recurrence/translate` | Creates and returns rrule. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/translate-recurrence-rrule-dto-collection/) |

### Recurring Payments

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `PUT` | `/api/element_register/mass/igualas/{ids}` | Replaces the Recurring Payments resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/put-mass-recurring-payments-item/) |
| `GET` | `/api/recurring payments` | Retrieves the collection of Recurring Payments resources. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/get-recurring-payments-collection/) |
| `DELETE` | `/api/recurring payments/{id}` | Removes the Recurring Payments resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-recurring-payments-item/) |
| `GET` | `/api/recurring payments/{id}` | Retrieves a Recurring Payments resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-recurring-payments-item/) |
| `POST` | `/api/recurring-payments` | Creates a Recurring Payments resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-recurring-payments-collection/) |
| `POST` | `/api/recurring-payments/concepts` | Creates a Recurring Payments resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-grouped-concepts-recurring-payments-collection/) |
| `POST` | `/api/recurring-payments/create-invoices` | Creates a Recurring Payments resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-create-recurring-payments-collection/) |
| `PATCH` | `/api/recurring-payments/mass/{ids}` | Updates the Recurring Payments resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/patch-mass-recurring-payments-item/) |
| `POST` | `/api/recurring-payments/preview` | Creates a Recurring Payments resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-priview-recurring-payments-collection/) |
| `PATCH` | `/api/recurring-payments/{id}` | Updates the Recurring Payments resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/patch-recurring-payments-item/) |

### Register

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/data-merger/{element}/{idElementParent}/{idElementChild}` | Data merger | `apiKey` | 3 | [↗](https://developers.sudespacho.net/docs/api-crm/get-data-merge-data-merger-collection/) |
| `POST` | `/api/element_register/bulk-deletion/{element}` | Asynchronous mass delete register. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-mass-element-registers-register-collection/) |
| `POST` | `/api/element_register/check-permissions/{element}` | Check permissions for all registers on a element | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/check-permissions-mass-element-registers-register-collection/) |
| `POST` | `/api/element_register/check-permissions/{element}/{id}` | Check permissions for an element and id given. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/check-element-register-permissions-register-item/) |
| `POST` | `/api/element_register/mass/{element}` | Creates a Register resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-mass-element-registries-register-collection/) |
| `DELETE` | `/api/element_register/mass/{element}/{ids}` | Asynchronous mass delete register. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-mass-element-register-register-collection/) |
| `PUT` | `/api/element_register/mass/{element}/{ids}` | Asynchronous mass update register. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/put-mass-element-register-register-collection/) |
| `POST` | `/api/element_register/{element}` | Create a new register. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/post-element-register-register-collection/) |
| `DELETE` | `/api/element_register/{element}/{id}` | Delete an register. | `apiKey` | 4 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-element-register-register-item/) |
| `GET` | `/api/element_register/{element}/{id}` | Retrieves a Register resource. | `apiKey` | 6 | [↗](https://developers.sudespacho.net/docs/api-crm/get-element-registry-register-item/) |
| `PUT` | `/api/element_register/{element}/{id}` | Update an register. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/put-element-register-register-collection/) |

### RelatedRegister

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/related_register/{element}/{id}` | Retrieves the collection of RelatedRegister resources. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/get-related-register-related-register-collection/) |

### RelatedRegistries

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/related_registries/{element}/{id}` | Retrieves the collection of RelatedRegistries resources. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/get-related-registries-related-registries-collection/) |

### RelationsElements

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `DELETE` | `/api/relation_element/{element}/{id}` | Delete an relations element. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-relation-element-relations-elements-collection/) |
| `POST` | `/api/relation_element/{element}/{id}` | Create a new relation element. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/post-relation-element-relations-elements-collection/) |
| `PUT` | `/api/relation_element/{element}/{id}` | Update an relations element. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/put-relation-element-relations-elements-collection/) |

### Remittances

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/remittances/create` | Returns a newly created register of selected of remittance element | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/create-remittance-remittances-collection/) |
| `POST` | `/api/remittances/export/{way}` | Returns a S3 presigned URL for a remittance export action | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/export-remittance-remittances-collection/) |
| `GET` | `/api/remittances/get-export-types` | Returns a newly created register of selected of remittance element | `apiKey` | 4 | [↗](https://developers.sudespacho.net/docs/api-crm/get-exports-remittances-collection/) |
| `POST` | `/api/remittances/preview` | Returns a preview of selected payments for remittance | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/preview-remittance-remittances-collection/) |
| `DELETE` | `/api/remittances/{id}` | Deletes a remittance and restores related payments | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-remittance-remittances-collection/) |

### Reports

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/report/{id}` | Get report detail. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-report-report-detail-collection/) |
| `GET` | `/api/reports` | Get reports collection. | `apiKey` | 17 | [↗](https://developers.sudespacho.net/docs/api-crm/get-reports-reports-collection/) |
| `POST` | `/api/reports/custom/predefined` | Install predefined custom reports. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-custom-report-install-predefined-custom-reports-collection/) |
| `POST` | `/api/reports/custom/{element}` | Create custom report. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-custom-report-custom-reports-collection/) |
| `GET` | `/api/reports/custom/{id}` | Execute stored custom report. | `apiKey` | 3 | [↗](https://developers.sudespacho.net/docs/api-crm/get-execute-custom-report-custom-reports-collection/) |
| `PATCH` | `/api/reports/custom/{id}` | Update custom report. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/patch-custom-report-custom-reports-collection/) |
| `GET` | `/api/reports/custom/{id}/export` | Export stored custom report to Excel. | `apiKey` | 3 | [↗](https://developers.sudespacho.net/docs/api-crm/get-export-custom-report-custom-reports-collection/) |
| `POST` | `/api/reports/{element}` | Create reports. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/post-reports-reports-collection/) |
| `DELETE` | `/api/reports/{element}/{id}` | Remove reports. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-reports-reports-collection/) |
| `PUT` | `/api/reports/{element}/{id}` | Update reports. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/put-reports-reports-collection/) |

### Restore Registers

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/restore_register/{element}/{id}` | Restore an register. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/restore-register-restore-register-collection/) |

### Series and Counters

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/autonumber` | Retrieves the collection of Series and Counters resources. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/get-series-and-counters-collection/) |
| `GET` | `/api/autonumber/{element}` | Retrieves a Series and Counters resource. | `apiKey` | 3 | [↗](https://developers.sudespacho.net/docs/api-crm/get-series-and-counters-item/) |

### Sms

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/sms/send_sms` | Send a Sms | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/send-sms-sms-collection/) |

### SudespachoAI

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/sudespachoai/ask` | Ask an AI model once. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-ask-sudespacho-ai-collection/) |
| `POST` | `/api/sudespachoai/converse` | Converse with an AI model. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-converse-sudespacho-ai-collection/) |
| `GET` | `/api/sudespachoai/limit` | Read the configured Sudespacho AI daily usage limit. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/get-limit-sudespacho-ai-collection/) |
| `POST` | `/api/sudespachoai/limit` | Create or update the Sudespacho AI daily usage limit. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-configure-limit-sudespacho-ai-collection/) |

### Tab

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/tabs/{element}` | Retrieves the collection of Tabs. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-tabs-tab-collection/) |
| `POST` | `/api/tabs/{element}` | Save the collection of Tabs. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/post-tabs-tab-collection/) |

### Tag

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/tags/{element}` | Create a new tag. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/post-tags-tag-collection/) |
| `DELETE` | `/api/tags/{element}/{id}` | Delete a tag. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-tags-tag-collection/) |
| `PUT` | `/api/tags/{element}/{id}` | Update a tag. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/put-tags-tag-collection/) |
| `GET` | `/api/tags/{id}` | Retrieves the collection of Tags. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/get-tags-tag-item/) |

### TaxZone

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/tax_zones` | Retrieves the collection of Tax Zones. | `apiKey` | 21 | [↗](https://developers.sudespacho.net/docs/api-crm/get-taxzone-resource-registries-tax-zone-collection/) |
| `GET` | `/api/tax_zones/read` | Retrieves the collection of Tax Zones. | `apiKey` | 20 | [↗](https://developers.sudespacho.net/docs/api-crm/retrieve-taxzone-register-tax-zone-collection/) |

### Taxes

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/taxes` | Retrieves the collection of Taxes resources. | `apiKey` | 17 | [↗](https://developers.sudespacho.net/docs/api-crm/get-taxes-collection/) |
| `POST` | `/api/taxes` | Create Tax. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-taxes-collection/) |
| `POST` | `/api/taxes/bulk/create/predefines/{ids}` | Create a new Tax given a group of templates. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/post-bulk-taxes-taxes-collection/) |
| `POST` | `/api/taxes/bulk/delete/{ids}` | Delete a list of Taxes. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-bulk-delete-taxes-collection/) |
| `POST` | `/api/taxes/obligation/{id}` | Create a new Tax from an old one. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/post-recurring-taxes-item/) |
| `POST` | `/api/taxes/predefined/{id}` | Creates a Taxes resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/post-template-taxes-item/) |
| `DELETE` | `/api/taxes/{id}` | Removes the Taxes resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-taxes-item/) |
| `GET` | `/api/taxes/{id}` | Retrieves a Taxes resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-taxes-item/) |
| `PATCH` | `/api/taxes/{id}` | Update Tax. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/patch-taxes-item/) |

### Taxes (massive creation)

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/taxes/mass` | Creates a Taxes (massive creation) resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-taxes-massive-creation-collection/) |

### Templates

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/templates/default/{type}/{way}` | Create a html template default for notifications. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/post-template-notifications-default-office-templates-collection/) |
| `POST` | `/api/templates/duplicate/{idTemplate}` | Duplicate template. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/post-template-notifications-duplicate-template-collection/) |
| `GET` | `/api/templates/html/detail/{idTemplate}` | Get detail html template. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-detail-html-template-templates-html-collection/) |
| `GET` | `/api/templates/html/{element}` | Get html templates collection. | `apiKey` | 18 | [↗](https://developers.sudespacho.net/docs/api-crm/get-html-templates-templates-html-collection-collection/) |
| `POST` | `/api/templates/html/{element}` | Create a html template. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/post-template-templates-html-collection/) |
| `PUT` | `/api/templates/html/{element}/{id}` | Update a html template. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/put-html-template-templates-html-collection/) |
| `GET` | `/api/templates/html/{idTemplate}/{element}/{idElement}` | Get html template. | `apiKey` | 3 | [↗](https://developers.sudespacho.net/docs/api-crm/get-html-template-templates-html-collection/) |
| `DELETE` | `/api/templates/html/{id}` | Remove html template. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-html-template-templates-html-collection/) |
| `POST` | `/api/templates/merger/html/{element}/{id}` | Get merged html template. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/post-merger-html-template-templates-html-collection/) |
| `POST` | `/api/templates/merger/notification/{element}/{id}` | Get merged notification template. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/post-merger-notification-template-templates-notification-collection/) |
| `GET` | `/api/templates/notification/detail/{idTemplate}` | Get detail notification template. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-detail-notification-template-templates-notification-collection/) |
| `POST` | `/api/templates/notification/{element}` | Create a notification template. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/post-template-templates-notification-collection/) |
| `PUT` | `/api/templates/notification/{element}/{id}` | Update a notification template. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/put-notification-template-templates-notification-collection/) |
| `GET` | `/api/templates/notification/{idTemplate}/{element}/{idElement}` | Get notification template. | `apiKey` | 3 | [↗](https://developers.sudespacho.net/docs/api-crm/get-notification-template-templates-notification-collection/) |
| `DELETE` | `/api/templates/notification/{id}` | Remove notification template. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-notification-template-templates-notification-collection/) |
| `GET` | `/api/templates/rtf/detail/{idTemplate}` | Get the detail of an rtf template. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-template-detail-templates-rtf-collection/) |
| `GET` | `/api/templates/rtf/{element}` | Get templates collection. | `apiKey` | 18 | [↗](https://developers.sudespacho.net/docs/api-crm/get-templates-templates-rtf-collection-collection/) |
| `POST` | `/api/templates/rtf/{element}` | Create a template. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/post-template-templates-rtf-collection/) |
| `PUT` | `/api/templates/rtf/{element}/{id}` | Update a template. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/put-template-templates-rtf-collection/) |
| `POST` | `/api/templates/rtf/{idTemplate}/{element}` | Generates PDF files from the provided element IDs and returns a ZIP archive containing them. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/multiple-template-templates-rtf-collection/) |
| `GET` | `/api/templates/rtf/{idTemplate}/{element}/{idElement}` | Get template. | `apiKey` | 3 | [↗](https://developers.sudespacho.net/docs/api-crm/get-template-templates-rtf-collection/) |
| `DELETE` | `/api/templates/rtf/{id}` | Remove template. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-template-templates-rtf-collection/) |

### Time Tracking Export Report

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/timetracking/report/{element}/{elementId}/export` | Retrieves the collection of Time Tracking Export Report resources. | `apiKey` | 8 | [↗](https://developers.sudespacho.net/docs/api-crm/get-time-tracking-export-report-collection/) |

### Time Tracking Report

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/timetracking/report/{element}/{elementId}` | Retrieves the collection of Time Tracking Report resources. | `apiKey` | 10 | [↗](https://developers.sudespacho.net/docs/api-crm/get-time-tracking-report-collection/) |

### Time Worked Report

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/timetracking/timeworked/employee/{employeeId}` | Retrieves the collection of Time Worked Report resources. | `apiKey` | 5 | [↗](https://developers.sudespacho.net/docs/api-crm/get-time-worked-report-collection/) |

### TimeTracking

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/timetracking` | Inputs hours worked. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/post-timetracking-time-tracking-collection/) |
| `GET` | `/api/timetracking/list` | Recovers Timetracking of a given Employee | `apiKey` | 18 | [↗](https://developers.sudespacho.net/docs/api-crm/get-timetracking-time-tracking-collection/) |
| `POST` | `/api/timetracking/qr/validate` |  | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/validate-qr-time-tracking-qr-collection/) |
| `DELETE` | `/api/timetracking/{id}` | Delete TimeTracking of User | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-timetracking-time-tracking-item/) |

### TimeTrackingConfig

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `DELETE` | `/api/timetracking/config/{element}/{elementId}` | Get Time tracking config details | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-time-tracking-config-item/) |
| `GET` | `/api/timetracking/config/{element}/{elementId}` | Get Time tracking config details | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/get-time-tracking-config-item/) |
| `POST` | `/api/timetracking/config/{element}/{elementId}` | Create new Time tracking config | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/create-time-tracking-config-collection/) |
| `PUT` | `/api/timetracking/config/{element}/{elementId}` | Get Time tracking config details | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/update-time-tracking-config-item/) |

### Upload

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/embedded_images` | Create embedded large images. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-embedded-large-image-embedded-large-images-collection/) |
| `GET` | `/api/files/presigned_download_url/{fileId}` | Presigned Download Url. | `apiKey` | 3 | [↗](https://developers.sudespacho.net/docs/api-crm/get-presigned-download-url-download-collection/) |
| `GET` | `/api/files/presigned_upload_url` | Presigned Upload Url. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/get-presigned-upload-url-upload-collection/) |

### VIDSigner

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `DELETE` | `/api/vidsigner` | Deletes VIDSigner integration. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-integration-vid-signer-collection/) |
| `GET` | `/api/vidsigner/credit` | Retrieves VIDSigner credit. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/get-credit-vid-signer-collection/) |
| `POST` | `/api/vidsigner/credit` | Manages VIDSigner credit. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/credit-configuration-vid-signer-collection/) |
| `GET` | `/api/vidsigner/integration` | Retrieves VIDSigner integration. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/get-integration-vid-signer-collection/) |
| `POST` | `/api/vidsigner/integration` | Creates VIDSigner integration. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/create-integration-vid-signer-collection/) |
| `POST` | `/api/vidsigner/recovery` | Creates a VIDSignerRecovery resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/vidsigner-recovery-vid-signer-recovery-collection/) |
| `GET` | `/api/vidsigner/report` | Retrieves VIDSigner report for signed document. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-report-vid-signer-collection/) |
| `POST` | `/api/vidsigner/send` | Sends a document to be signed. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/send-document-vid-signer-collection/) |
| `POST` | `/api/vidsigner/status/{office}/docstatus/{DocGUI}` | Creates a VIDSignerUnauthorized resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/update-status-vid-signer-unauthorized-collection/) |

### View

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/merge-tags/{element}` | Get collection of elements with their relations and tags for merging | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-file-template-merge-tags-collection/) |
| `GET` | `/api/view/complete/{id}` | Retrieves a CompleteView resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-complete-view-item/) |
| `GET` | `/api/view/enums/absences/{fieldName}` | Retrieves the collection of EnumsView resources. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-enums-absences-enums-view-collection/) |
| `GET` | `/api/view/enums/{elementName}/{elementPropertyName}` | Retrieves the collection of EnumsView resources. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/get-enums-enums-view-collection/) |
| `GET` | `/api/view/global_quick_search/{element}` | Retrieves the collection of GlobalQuickSearchView resources. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-global-quick-search-global-quick-search-view-collection/) |
| `POST` | `/api/view/list/{element}` | Create a new View List. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/post-view-list-list-view-collection/) |
| `DELETE` | `/api/view/list/{element}/{viewName}/{idUser}` | Reset view list. | `apiKey` | 3 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-view-list-list-view-collection/) |
| `GET` | `/api/view/list/{id}` | Retrieves a ListView resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-list-view-item/) |
| `GET` | `/api/view/mass_update/{id}` | Retrieves a MassUpdateView resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-mass-update-view-item/) |
| `GET` | `/api/view/preview_view/{element}` | Retrieves the collection of PreviewView resources. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-preview-view-preview-view-collection/) |
| `GET` | `/api/view/quick_creation/{element}` | Retrieves the collection of QuickCreationView resources. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-global-quick-search-quick-creation-view-collection/) |
| `GET` | `/api/view/quick_filters/{id}` | Retrieves a QuickFiltersView resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-quick-filters-view-item/) |
| `GET` | `/api/view/relation/{id}` | Retrieves a RelationsView resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-relations-view-item/) |
| `GET` | `/api/view/search/{id}` | Retrieves a SearchView resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-search-view-item/) |

### View Config

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/view/config` | List view configuration records | `apiKey` | 6 | [↗](https://developers.sudespacho.net/docs/api-crm/list-config-views-view-config-collection/) |
| `POST` | `/api/view/config` | Create (or update if exists) a config view | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/create-config-view-view-config-item/) |
| `GET` | `/api/view/config/{element}/fields` | List available fields for a view configuration | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/list-config-view-fields-view-config-collection/) |
| `GET` | `/api/view/config/{element}/relations` | List parent and child relations for an element | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/list-config-view-relations-view-config-collection/) |
| `DELETE` | `/api/view/config/{id}` | Delete a config view value | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-config-view-view-config-item/) |
| `PATCH` | `/api/view/config/{id}` | Update a config view value | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/update-config-view-view-config-item/) |
| `GET` | `/api/view/config/{id}/data` | Get serialized data for a config view | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/config-view-data-view-config-item/) |
| `PATCH` | `/api/view/config/{id}/field` | Update a personalized extension value (only "activo" field value) | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/update-config-view-fields-view-config-item/) |

### ViewConfig

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `GET` | `/api/view_configs` | Retrieves the collection of ViewConfig resources. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/get-view-config-collection/) |
| `GET` | `/api/view_configs/{id}` | Retrieves a ViewConfig resource. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-view-config-item/) |

### WhatsApp

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `DELETE` | `/api/whatsapp` | Deletes WhatsApp integration. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-integration-whats-app-collection/) |
| `POST` | `/api/whatsapp` | Creates WhatsApp integration. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/create-integration-whats-app-collection/) |
| `POST` | `/api/whatsapp/create_message_register` | Sends a WhatsApp message | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/create-message-register-whats-app-collection/) |
| `GET` | `/api/whatsapp/get_media` | Retrieves received WhatsApp messages media. | `apiKey` | 3 | [↗](https://developers.sudespacho.net/docs/api-crm/get-media-whats-app-collection/) |
| `GET` | `/api/whatsapp/get_messages` | Retrieves received WhatsApp messages. | `apiKey` | 2 | [↗](https://developers.sudespacho.net/docs/api-crm/get-messages-whats-app-collection/) |
| `GET` | `/api/whatsapp/get_phone` | Retrieves phone number. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/get-phone-whats-app-collection/) |
| `POST` | `/api/whatsapp/send_message` | Sends a WhatsApp message | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/send-message-whats-app-collection/) |

### Widgets

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/widget` | Create a Widget. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/post-widget-widget-collection/) |
| `GET` | `/api/widget/{idWidget}` | Get Widget detail. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-widget-widget-collection/) |
| `DELETE` | `/api/widget/{id}` | Remove widget. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-widget-widget-collection/) |
| `PUT` | `/api/widget/{id}` | Update a widget. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/put-widget-widget-collection/) |
| `GET` | `/api/widgets/all` | Get Widgets collection. | `apiKey` | 17 | [↗](https://developers.sudespacho.net/docs/api-crm/get-widgets-all-widgets-collection/) |

### WorkGraphics

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `POST` | `/api/workgraphics/export` | Returns the file contents of file to export | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/export-data-work-graphics-collection/) |
| `POST` | `/api/workgraphics/graphics` | Returns specified views | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/read-graphics-work-graphics-collection/) |
| `GET` | `/api/workgraphics/properties/{type}/{id}` | Recovers WorkGraphics of a given Employee | `apiKey` | 4 | [↗](https://developers.sudespacho.net/docs/api-crm/get-properties-work-graphics-collection/) |
| `POST` | `/api/workgraphics/view` | Recovers WorkGraphics of a given Employee | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/read-view-work-graphics-collection/) |
| `GET` | `/api/workgraphics/view/list` | Recovers WorkGraphics of a given Employee | `apiKey` | 3 | [↗](https://developers.sudespacho.net/docs/api-crm/list-views-work-graphics-collection/) |

### Zadarma

| Método | Path | Resumen | Auth | Params | Doc |
|---|---|---|---|---|---|
| `DELETE` | `/api/zadarma` | Deletes Zadarma integration. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/delete-integration-zadarma-dto-collection/) |
| `GET` | `/api/zadarma` | Retrieves Zadarma integration. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/get-integration-zadarma-dto-collection/) |
| `POST` | `/api/zadarma` | Creates Zadarma integration. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/create-integration-zadarma-dto-collection/) |
| `GET` | `/api/zadarma/callback` | Request callback. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-request-callback-zadarma-dto-collection/) |
| `POST` | `/api/zadarma/extension` | Creates Zadarma extension linked to a user. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/create-extension-zadarma-dto-collection/) |
| `GET` | `/api/zadarma/extension/{id}` | Retrieves Zadarma extensions. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/get-extension-zadarma-dto-collection/) |
| `GET` | `/api/zadarma/record` | Retrieves Zadarma call record. | `apiKey` | 1 | [↗](https://developers.sudespacho.net/docs/api-crm/get-record-zadarma-dto-collection/) |
| `GET` | `/api/zadarma/status/{office}` | Retrieves the collection of ZadarmaUnauthorized resources. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/unauthorized-get-zadarma-unauthorized-collection/) |
| `POST` | `/api/zadarma/status/{office}` | Creates a ZadarmaUnauthorized resource. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/unauthorized-post-zadarma-unauthorized-collection/) |
| `GET` | `/api/zadarma/webrtc` | Retrieves Zadarma key for the webrtc-widget. | `apiKey` | 0 | [↗](https://developers.sudespacho.net/docs/api-crm/get-webrtc-key-zadarma-dto-collection/) |

## Paths declarados sin operación documentada

Entradas de `paths` que el OpenAPI declara con `parameters` pero **sin** operación (GET/POST/…). No son endpoints ocultos; su verbo real, si existe, se confirma por sondeo empírico (Fase B). No se descartan para no ocultar superficie.

| Path | Claves declaradas |
|---|---|
| `/api/access_registers` | parameters |
| `/api/access_registers/{id}` | parameters |
| `/api/audit_registers` | parameters |
| `/api/companies` | parameters |
| `/api/create_folders` | parameters |
| `/api/data_exporters` | parameters |
| `/api/data_exporters/{id}` | parameters |
| `/api/data_importers` | parameters |
| `/api/data_importers/{id}` | parameters |
| `/api/data_migrations` | parameters |
| `/api/default_office_templates` | parameters |
| `/api/delete_folders` | parameters |
| `/api/duplicate_templates` | parameters |
| `/api/edit_folders` | parameters |
| `/api/element_registries` | parameters |
| `/api/embedded_large_images` | parameters |
| `/api/enums_views` | parameters |
| `/api/enums_views/{id}` | parameters |
| `/api/file_templates` | parameters |
| `/api/folders` | parameters |
| `/api/folders_permissions` | parameters |
| `/api/global_quick_search_views` | parameters |
| `/api/global_quick_search_views/{id}` | parameters |
| `/api/groups` | parameters |
| `/api/groups/{id}` | parameters |
| `/api/integrations` | parameters |
| `/api/lists` | parameters |
| `/api/merge_tags` | parameters |
| `/api/notifications` | parameters |
| `/api/office_configurations` | parameters |
| `/api/office_service_statuses` | parameters |
| `/api/office_services` | parameters |
| `/api/office_unauthorized_configurations` | parameters |
| `/api/permissions` | parameters |
| `/api/personal_configs` | parameters |
| `/api/predefined_details` | parameters |
| `/api/predefined_use_folders` | parameters |
| `/api/predefined_uses` | parameters |
| `/api/predefineds` | parameters |
| `/api/preview_views` | parameters |
| `/api/quick_creation_views` | parameters |
| `/api/quick_creation_views/{id}` | parameters |
| `/api/registers` | parameters |
| `/api/registers/{id}` | parameters |
| `/api/related_registers` | parameters |
| `/api/related_registries` | parameters |
| `/api/relations_elements` | parameters |
| `/api/relations_elements/{id}` | parameters |
| `/api/report_details` | parameters |
| `/api/restore_registers` | parameters |
| `/api/summation_element_registries` | parameters |
| `/api/summation_element_registries/{id}` | parameters |
| `/api/tabs` | parameters |
| `/api/tags` | parameters |
| `/api/templates_html_collections` | parameters |
| `/api/templates_htmls` | parameters |
| `/api/templates_notifications` | parameters |
| `/api/templates_rtf_collections` | parameters |
| `/api/templates_rtfs` | parameters |
| `/api/use_companies` | parameters |
| `/api/users` | parameters |
| `/api/widgets` | parameters |

