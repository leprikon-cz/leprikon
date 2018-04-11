// Handles popup links.

(function($) {
    $(document).ready(function() {
        $('body').on('click', '.popup-link', function(e) {
            e.preventDefault();
            var href = this.href;
            if (href.indexOf('?') === -1) {
                href += '?_popup=1';
            } else {
                href += '&_popup=1';
            }
            var win = window.open(href, href, 'resizable=yes,scrollbars=yes');
            win.focus();
            return false;
        });
    });
})(django.jQuery);
