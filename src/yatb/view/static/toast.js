/**
 * @author Script47 (https://github.com/Script47/Toast)
 * @description Toast - A Bootstrap 4.2+ jQuery plugin for the toast component
 * @version 1.2.0
 *
 * 4/3/21 CG: Massive edits to support bootstrap 5.x
 *
 * TODO:
 *
 * (1) Need to handle new placement
 *     https://getbootstrap.com/docs/5.0/components/toasts/#placement
 *     It is NOT top-right, top-left anymore but more granular classes are needed
 *
 *
 **/
(function ($) {

    // (1) Container
    //     Need to handle the placement, currently hardcoded here
    const TOAST_CONTAINER_HTML = `<div aria-live="polite" aria-atomic="true" class="position-relative">
                                    <div id="toast-container" class="toast-container position-absolute top-0 end-0 p-3">
                                    </div>
                                 </div>`;
    // (2) Set some defaults
    $.toastDefaults = {
        position: 'top-right',
        dismissible: true,
        stackable: true,
        pauseDelayOnHover: true,
        style: {
            toast: '',
            info: '',
            success: '',
            warning: '',
            error: '',
        }
    };
    // (3) Cleanup function
    $('body').on('hidden.bs.toast', '.toast', function () {
        $(this).remove();
    });
    // (4) Counter
    let toastRunningCount = 1;

    // ============================================================================================
    // (5) Main function
    // ============================================================================================

    function render(opts) {

        // (6) No container, create our own
        if (!$('#toast-container').length) {
            // (7) TODO: Get the new placement
            const position = ['top-right', 'top-left', 'top-center', 'bottom-right', 'bottom-left', 'bottom-center'].includes($.toastDefaults.position) ? $.toastDefaults.position : 'top-right';
            $('body').prepend(TOAST_CONTAINER_HTML);
            $('#toast-container').addClass(position);
        }

        // (7) Finalize all the options, merge defaults with what was passed in
        let toastContainer = $('#toast-container');
        let html = '';
        let classes = {
            header: {
                fg: '',
                bg: ''
            },
            subtitle: 'text-white',
            dismiss: 'text-white'
        };
        let id = opts.id || `toast-${toastRunningCount}`;
        let type = opts.type;
        let title = opts.title;
        let subtitle = opts.subtitle;
        let content = opts.content;
        let img = opts.img;
        let delayOrAutohide = opts.delay ? `data-delay="${opts.delay}"` : `data-autohide="false"`;
        let hideAfter = ``;
        let dismissible = $.toastDefaults.dismissible;
        let globalToastStyles = $.toastDefaults.style.toast;
        let paused = false;

        if (typeof opts.dismissible !== 'undefined') {
            dismissible = opts.dismissible;
        }

        // (8) Set specific class names
        switch (type) {
            case 'info':
                classes.header.bg = $.toastDefaults.style.info || 'bg-info';
                classes.header.fg = $.toastDefaults.style.info || 'text-white';
                break;

            case 'success':
                classes.header.bg = $.toastDefaults.style.success || 'bg-success';
                classes.header.fg = $.toastDefaults.style.info || 'text-white';
                break;

            case 'warning':
                classes.header.bg = $.toastDefaults.style.warning || 'bg-warning';
                classes.header.fg = $.toastDefaults.style.warning || 'text-white';
                break;

            case 'error':
            case 'danger':
                classes.header.bg = $.toastDefaults.style.error || 'bg-danger';
                classes.header.fg = $.toastDefaults.style.error || 'text-white';
                break;
        }

        // (9) Set the delay
        if ($.toastDefaults.pauseDelayOnHover && opts.delay) {
            delayOrAutohide = `data-autohide="false"`;
            hideAfter = `data-hide-after="${Math.floor(Date.now() / 1000) + (opts.delay / 1000)}"`;
        }

        // (10) If there is a `title`
        if (title) {
            html = `<div id="${id}" class="toast ${globalToastStyles}" role="alert" aria-live="assertive" aria-atomic="true" ${delayOrAutohide} ${hideAfter}>`;
            _dimissable = '';
            _subtitle = '';
            _img = '';
            if (dismissible) {
                _dismissable = '<button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>';
            }
            if (subtitle) {
                _subtitle = `<small>${subtitle}</small>`;
            }
            if (img) {
                //_img = `<img src="..." class="rounded me-2" alt="...">`;
            }
            // html += `<div class="toast-header">
            //
            //            <strong class="me-auto">${title}</strong>
            //            <small>11 mins ago</small>
            //            <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
            //          </div>`;
            html += `<div class="toast-header ${classes.header.bg} ${classes.header.fg}">
                        ${_img}
                        <strong class="me-auto">${title}</strong>
                        ${_subtitle}
                        ${_dismissable}
                     </div>`;
            if (content) {
                html += `<div class="toast-body">
                            ${content}
                         </div>`;
            }
            html += `</div>`;
        // (11) If there is no title, we have to put the color into the actual
        } else {
            html = `<div id="${id}" class="toast ${globalToastStyles} ${classes.header.bg} ${classes.header.fg}" role="alert" aria-live="assertive" aria-atomic="true" ${delayOrAutohide} ${hideAfter}>`;
            if (content) {
                // If we don't have the title, we need to add the dismissable
                if (dismissible) {
                    html += `<div class="d-flex">
                               <div class="toast-body">
                                 ${content}
                               </div>
                               <button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                             </div>`;
                } else {
                    html += `<div class="toast-body">
                               ${content}
                             </div>`;
                }
            }
            html += `</div>`;
        }
        // (12) Set stackable
        if (!$.toastDefaults.stackable) {
            toastContainer.find('.toast').each(function () {
                $(this).remove();
            });
            toastContainer.append(html);
            toastContainer.find('.toast:last').toast('show');
        } else {
            toastContainer.append(html);
            toastContainer.find('.toast:last').toast('show');
        }
        // (13) Deal with the delay
        if ($.toastDefaults.pauseDelayOnHover) {
            setTimeout(function () {
                if (!paused) {
                    $(`#${id}`).toast('hide');
                }
            }, opts.delay);
            $('body').on('mouseover', `#${id}`, function () {
                paused = true;
            });
            $(document).on('mouseleave', '#' + id, function () {
                const current = Math.floor(Date.now() / 1000),
                    future = parseInt($(this).data('hideAfter'));

                paused = false;

                if (current >= future) {
                    $(this).toast('hide');
                }
            });
        }
        // (14) Increment the counter
        toastRunningCount++;
    }

    /**
     * Show a snack
     * @param type
     * @param title
     * @param delay
     */
    $.snack = function (type, content, delay) {
        return render({
            type,
            content,
            delay
        });
    }

    /**
     * Show a toast
     * @param opts
     */
    $.toast = function (opts) {
        return render(opts);
    }

}(jQuery));
