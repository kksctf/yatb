function value_handler(ret, name, value, list = false) {
    var parts = name.split(".");
    fdict = ret;
    parts.slice(0, -1).forEach((val) => {
        if (!fdict.hasOwnProperty(val))
            fdict[val] = {};
        fdict = fdict[val];
    });
    if (!list)
        fdict[parts[parts.length - 1]] = value;
    else {
        if (fdict[parts[parts.length - 1]] == undefined) {
            fdict[parts[parts.length - 1]] = []
        }
        fdict[parts[parts.length - 1]].push(value);
    }
}

function getFormData(f) {
    var inputs = $(f).find(":input");
    var ret = {};
    $(inputs).each(function (index, obj) {
        obj_j = $(obj);
        obj_name = obj.name;
        obj_type = obj.type;
        if (obj_name !== undefined && obj_name != "" && !obj_j.hasClass("form_class_disabled")) {
            if (obj_type !== undefined && obj_name != "") {
                if (obj_type == "checkbox") {
                    if (obj_j.val() != "on") {
                        if (obj.checked)
                            value_handler(ret, obj_name, obj_j.val(), list = true);
                    }
                    else
                        value_handler(ret, obj_name, obj.checked);
                }
                else
                    value_handler(ret, obj_name, obj_j.val());
            }
            else
                value_handler(ret, obj_name, obj_j.val());
        }
    });
    console.log("NEW", ret);
    return ret;
}


function init_form_class() {
    $("select.form_class_selector").change(function () {
        var selected = this.value;
        var propname = this.dataset["propname"];
        var div = $(".form_class_selector_list > .form_class_selector_class[data-ref=" + selected + "][data-propname=" + propname + "]");
        var other_div = $(".form_class_selector_list > .form_class_selector_class[data-ref!=" + selected + "][data-propname=" + propname + "]");
        div.find(":input").removeClass("form_class_disabled").prop( "disabled", false);
        other_div.find(":input").addClass("form_class_disabled").prop( "disabled", true);
        div.show();
        other_div.hide();
        console.log(selected, div, other_div);
    });
    $("select.form_class_selector").change();
}

function api_req(form, api, toast_name, method = "POST", ok_callback = (data) => { }, error_callback = (data) => { }, supress_ok = false, async = true) {
    var data = undefined;
    if (form != undefined)
        var data = getFormData(form);
    $.ajax({
        type: method,
        url: api,
        data: data ? JSON.stringify(data) : undefined,
        contentType: 'application/json',
        async: async,
        success: function (data) {
            console.log("OnSucc", data);
            if (!supress_ok) {
                $.toast({
                    type: 'success',
                    title: toast_name,
                    subtitle: 'now',
                    content: '<pre>' + JSON.stringify(data) + '</pre>',
                    delay: 5000,
                });
            }
            ok_callback(data);
        },
        error: function (data) {
            console.warn("ERROR", data);
            $.toast({
                type: 'error',
                title: toast_name,
                subtitle: 'now',
                content: data.responseText,
                delay: 5000,
            });
            error_callback(data);
        },
    });
}

var api_url = {};
