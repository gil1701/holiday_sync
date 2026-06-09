frappe.ui.form.on('Company', {
    refresh: function(frm) {
        if (!frm.is_new()) {
            frm.add_custom_button(__('Sync Holidays from Google'), function() {
                frappe.prompt([
                    {
                        fieldname: 'year',
                        fieldtype: 'Int',
                        label: __('Year'),
                        default: new Date().getFullYear(),
                        reqd: 1
                    }
                ], function(values) {
                    frappe.call({
                        method: 'holiday_sync.utils.sync_company_holidays',
                        args: {
                            company: frm.doc.name,
                            year: values.year
                        },
                        freeze: true,
                        freeze_message: __('Syncing holidays from Google Calendar...'),
                        callback: function(r) {
                            if (!r.exc) {
                                frm.reload_doc();
                            }
                        }
                    });
                }, __('Sync Holidays'), __('Sync'));
            }, __('Actions'));
        }
    }
});