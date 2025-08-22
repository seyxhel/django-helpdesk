$(() => {
    // Do not initialize legacy jQuery UI datepickers when a page requests
    // the modern/native date control. Pages can set
    // `window.HELPDESK_DISABLE_LEGACY_DATEPICKER = true` before scripts run.
    if (window.HELPDESK_DISABLE_LEGACY_DATEPICKER) return;
    $(".date-field").datepicker({dateFormat: 'yy-mm-dd'});
});
$(() => {
    if (window.HELPDESK_DISABLE_LEGACY_DATEPICKER) return;
    $(".datetime-field").datepicker({dateFormat: 'yy-mm-dd 00:00:00'});
});
$(() => {
    // TODO: This does not work as written, need to make functional
    $(".time-field").tooltip="Time format 24hr: 00:00:00";
});