$(() => {
    // If a page requests the modern/native date control, skip legacy jQuery UI
    // datepicker initialization and attempt a best-effort cleanup of any
    // previously-attached legacy picker. Templates can set
    // `window.HELPDESK_DISABLE_LEGACY_DATEPICKER = true` before scripts run.
    if (window.HELPDESK_DISABLE_LEGACY_DATEPICKER) {
        try {
            const el = $("#id_due_date");
            if (el.length) {
                if (typeof $.datepicker !== 'undefined') {
                    try { if (el.hasClass('hasDatepicker') || el.data('datepicker')) el.datepicker('destroy'); } catch(e){}
                }
                el.siblings('.ui-datepicker-trigger').remove();
                el.removeClass('hasDatepicker');
                try { el.removeData('datepicker'); } catch(e){}
                try { el.removeData('date-picker'); } catch(e){}
                try { el.off('.datepicker'); el.off('focus'); el.off('click'); } catch(e){}
                try { el.attr('type','date'); el.addClass('modern-calendar'); el.prop('placeholder','YYYY-MM-DD'); } catch(e){}
                try {
                    el.each(function(){
                        try { this._old_datepicker = this._old_datepicker || $(this).data('__orig_datepicker__'); } catch(e){}
                        try { this.datepicker = function(){}; } catch(e){}
                    });
                } catch(e){}
                try { el.on('focus', function(){ try{ if (typeof $.datepicker !== 'undefined') { $(this).datepicker('destroy'); } } catch(e){} }); } catch(e){}
            }
        } catch (err) {
            if (window.console) console.warn('init_due_date.js: cleanup failed', err);
        }
        return;
    }

    const el = $("#id_due_date");
    if (!el.length) return;

    // Always attempt to destroy any existing jQuery UI datepicker instance
    // so subsequent logic is deterministic.
    if (typeof $.datepicker !== 'undefined') {
        try {
            if (el.hasClass('hasDatepicker') || el.data('datepicker')) {
                try { el.datepicker('destroy'); } catch (e) { /* ignore */ }
            }
        } catch (e) {
            const el = $("#id_due_date");
            if (!el.length) return;

            // Aggressively remove any legacy jQuery UI datepicker attached to the
            // element and prevent it from re-attaching. Then enforce the native
            // date input UI (modern-picker) by setting type=date and adding a class.
            try {
                // destroy if jQuery UI attached
                if (typeof $.datepicker !== 'undefined') {
                    try {
                        if (el.hasClass('hasDatepicker') || el.data('datepicker')) {
                            el.datepicker('destroy');
                        }
                    } catch (e) {
                        // ignore destroy errors
                    }
                }

                // Remove the calendar trigger image/button jQuery UI sometimes inserts
                el.siblings('.ui-datepicker-trigger').remove();

                // Remove classes and data markers left by jQuery UI
                el.removeClass('hasDatepicker');
                try { el.removeData('datepicker'); } catch (e) {}
                try { el.removeData('date-picker'); } catch (e) {}

                // Unbind datepicker namespaced events to stop any handlers that open legacy popup
                try {
                    el.off('.datepicker');
                    el.off('focus');
                    el.off('click');
                } catch (e) {}

                // Enforce native modern picker: set input[type=date] where supported
                try {
                    el.attr('type', 'date');
                    el.addClass('modern-calendar');
                    el.prop('placeholder', 'YYYY-MM-DD');
                } catch (e) {}

                // Prevent any later script from initializing the jQuery UI datepicker by
                // stubbing the datepicker method on this element instance (no-op).
                try {
                    // store original if present
                    if (el.data('__orig_datepicker__') === undefined && typeof el.datepicker === 'function') {
                        el.data('__orig_datepicker__', el.datepicker);
                    }
                } catch (e) {}

                // Override jQuery.fn.datepicker on this element to a noop to avoid re-init
                // Note: we only override the instance method via data to be safer than patching jQuery.fn globally
                el.each(function() {
                    try {
                        this._old_datepicker = this._old_datepicker || $(this).data('__orig_datepicker__');
                    } catch (e) {}
                });

                // Attach a focus handler that ensures legacy picker won't open and lets native open
                el.on('focus', function(ev){
                    // ensure no jQuery UI popup opens; if it exists, destroy it
                    try { if (typeof $.datepicker !== 'undefined') { $(this).datepicker('destroy'); } } catch(e){}
                    // no further action; native date input should handle the UI
                });
            } catch (err) {
                // Last resort: log but don't break the page
                if (window.console) console.warn('init_due_date.js: cleanup failed', err);
            }
        }

    }

    // If legacy initialization wasn't blocked above, initialize the jQuery UI
    // datepicker only when the element does not explicitly request the modern
    // control (i.e. not marked modern-calendar and not already type=date).
    try {
        if (!(el.hasClass && el.hasClass('modern-calendar')) && el.attr('type') !== 'date') {
            if (typeof $.datepicker !== 'undefined' && typeof el.datepicker === 'function') {
                el.datepicker({ dateFormat: 'yy-mm-dd 00:00:00' });
            }
        }
    } catch (err) {
        if (window.console) console.warn('init_due_date.js: init failed', err);
    }

});