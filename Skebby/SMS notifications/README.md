# Skebby notifications

Save file in: ~/local/share/check_mk/notifications (chmod it with 755)

From Skebby web page:

To set a custom Skebby user go here from the owner account: https://messenger.skebby.it/profile/manage

And then set API password here (API password must be set, it's not the user account password): https://messenger.skebby.it/account

In CheckMK: Go in Checkmk, Setup->Notifications. Add new Notification rule and select notification method "SMS using Skebby.it via https" and "Call with the following parameters". In first field select Skebby API username and in second field Skebby API password. Then set the user that receinve the alert. In users set the pager field with the full telephone number. Es. 39348(ecc)

Set match hosts, services and Match service event type. Finally test creating fake check results in the host service.