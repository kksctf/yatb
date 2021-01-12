function generate_kek() {
    var toolbarBuiltInButtons = {
        'bold': {
            name: 'bold',
            action: EasyMDE.toggleBold,
            className: 'fa fa-bold',
            title: 'Bold',
            default: true,
        },
        'italic': {
            name: 'italic',
            action: EasyMDE.toggleItalic,
            className: 'fa fa-italic',
            title: 'Italic',
            default: true,
        },
        'strikethrough': {
            name: 'strikethrough',
            action: EasyMDE.toggleStrikethrough,
            className: 'fa fa-strikethrough',
            title: 'Strikethrough',
        },
        'heading': {
            name: 'heading',
            action: EasyMDE.toggleHeadingSmaller,
            className: 'fa fa-header fa-heading',
            title: 'Heading',
            default: true,
        },
        'heading-smaller': {
            name: 'heading-smaller',
            action: EasyMDE.toggleHeadingSmaller,
            className: 'fa fa-header fa-heading header-smaller',
            title: 'Smaller Heading',
        },
        'heading-bigger': {
            name: 'heading-bigger',
            action: EasyMDE.toggleHeadingBigger,
            className: 'fa fa-header fa-heading header-bigger',
            title: 'Bigger Heading',
        },
        'heading-1': {
            name: 'heading-1',
            action: EasyMDE.toggleHeading1,
            className: 'fa fa-header fa-heading header-1',
            title: 'Big Heading',
        },
        'heading-2': {
            name: 'heading-2',
            action: EasyMDE.toggleHeading2,
            className: 'fa fa-header fa-heading header-2',
            title: 'Medium Heading',
        },
        'heading-3': {
            name: 'heading-3',
            action: EasyMDE.toggleHeading3,
            className: 'fa fa-header fa-heading header-3',
            title: 'Small Heading',
        },
        'separator-1': {
            name: 'separator-1',
        },
        'code': {
            name: 'code',
            action: EasyMDE.toggleCodeBlock,
            className: 'fa fa-code',
            title: 'Code',
        },
        'quote': {
            name: 'quote',
            action: EasyMDE.toggleBlockquote,
            className: 'fa fa-quote-left',
            title: 'Quote',
            default: true,
        },
        'unordered-list': {
            name: 'unordered-list',
            action: EasyMDE.toggleUnorderedList,
            className: 'fa fa-list-ul',
            title: 'Generic List',
            default: true,
        },
        'ordered-list': {
            name: 'ordered-list',
            action: EasyMDE.toggleOrderedList,
            className: 'fa fa-list-ol',
            title: 'Numbered List',
            default: true,
        },
        'clean-block': {
            name: 'clean-block',
            action: EasyMDE.cleanBlock,
            className: 'fa fa-eraser',
            title: 'Clean block',
        },
        'separator-2': {
            name: 'separator-2',
        },
        'link': {
            name: 'link',
            action: EasyMDE.drawLink,
            className: 'fa fa-link',
            title: 'Create Link',
            default: true,
        },
        'image': {
            name: 'image',
            action: EasyMDE.drawImage,
            className: 'fa fa-image',
            title: 'Insert Image',
            default: true,
        },
        'upload-image': {
            name: 'upload-image',
            action: EasyMDE.drawUploadedImage,
            className: 'fa fa-image',
            title: 'Import an image',
        },
        'table': {
            name: 'table',
            action: EasyMDE.drawTable,
            className: 'fa fa-table',
            title: 'Insert Table',
        },
        'horizontal-rule': {
            name: 'horizontal-rule',
            action: EasyMDE.drawHorizontalRule,
            className: 'fa fa-minus',
            title: 'Insert Horizontal Line',
        },
        'separator-3': {
            name: 'separator-3',
        },
        'preview': {
            name: 'preview',
            action: EasyMDE.togglePreview,
            className: 'fa fa-eye',
            noDisable: true,
            title: 'Toggle Preview',
            default: true,
        },
        'side-by-side': {
            name: 'side-by-side',
            action: EasyMDE.toggleSideBySide,
            className: 'fa fa-columns',
            noDisable: true,
            noMobile: true,
            title: 'Toggle Side by Side',
            default: true,
        },
        'fullscreen': {
            name: 'fullscreen',
            action: EasyMDE.toggleFullScreen,
            className: 'fa fa-arrows-alt',
            noDisable: true,
            noMobile: true,
            title: 'Toggle Fullscreen',
            default: true,
        },
        'separator-4': {
            name: 'separator-4',
        },
        'guide': {
            name: 'guide',
            action: 'https://www.markdownguide.org/basic-syntax/',
            className: 'fa fa-question-circle',
            noDisable: true,
            title: 'Markdown Guide',
            default: true,
        },
        'separator-5': {
            name: 'separator-5',
        },
        'undo': {
            name: 'undo',
            action: EasyMDE.undo,
            className: 'fa fa-undo',
            noDisable: true,
            title: 'Undo',
        },
        'redo': {
            name: 'redo',
            action: EasyMDE.redo,
            className: 'fa fa-repeat fa-redo',
            noDisable: true,
            title: 'Redo',
        },
    };

    toolbar = [];
    showIcons = ['strikethrough', 'code', 'table', 'redo', 'heading', 'undo', 'heading-bigger', 'heading-smaller', 'heading-1', 'heading-2', 'heading-3', 'clean-block', 'horizontal-rule'];

    // Loop over the built in buttons, to get the preferred order
    for (var key in toolbarBuiltInButtons) {
        if (Object.prototype.hasOwnProperty.call(toolbarBuiltInButtons, key)) {
            if (key.indexOf('separator-') != -1) {
                toolbar.push('|');
            }

            if (toolbarBuiltInButtons[key].default === true || (showIcons && showIcons.constructor === Array && showIcons.indexOf(key) != -1)) {
                toolbar.push(key);
            }
        }
    }

    return toolbar;
}

function easy_mde_runner(element, draft_name) {
    var easyMDE = new EasyMDE({
        element: element,
        autosave: {
            enabled: true,
            // uniqueId: 'mde-autosave-draft',
            uniqueId: "mde-autosave-" + draft_name,
        },
        forceSync: true,
        promptURLs: true,
        nativeSpellcheck: false,
        previewImagesInEditor: false,
        toolbar: generate_kek().concat([
            "|",
            {
                name: "toggle-image-prev",
                action: function image_preview_toggle(editor) {
                    if (easyMDE.options.previewImagesInEditor !== undefined) {
                        easyMDE.options.previewImagesInEditor = !easyMDE.options.previewImagesInEditor;
                    }
                    else
                        easyMDE.options.previewImagesInEditor = false;

                },
                className: "fa fa-star",
                title: "Toggle image preview (not work yet)",
            },
        ]),
    });
}

