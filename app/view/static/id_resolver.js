user_id_cache = JSON.parse(localStorage.getItem("user_id_cache")) || {};
task_id_cache = JSON.parse(localStorage.getItem("task_id_cache")) || {};

// user_id_cache = {};
// task_id_cache = {};

$("#flag_submit_form").submit(function (event) {
    event.preventDefault();

    req(api_list["api_task_submit_flag"], { data: getFormData(this), })
        .then(get_json)
        .then(ok_toast_generator("Solve flag"), nok_toast_generator("Solve flag"))
        .then((resp) => {
            console.log(resp);
            if (resp.json.includes('-')) {
                var task = $("div[data-id=" + resp.json + "]");
                task.addClass("solved");
                console.log("found task", task);
            }
        })
});

$(function () {
    const resolver_settings = [
        { class: "user_id_resolve", api_url: "api_users_get_username", path_key: "user_id", result_key: "", cache: user_id_cache },
        { class: "task_id_resolve", api_url: "api_task_get", path_key: "task_id", result_key: "task_name", cache: task_id_cache },
    ]
    resolver_settings.forEach(async function (item) {
        let item_list = [];
        $("." + item.class).each(function (index) { item_list.push(this); });
        for (item_index in item_list) {
            othis = item_list[item_index]
            let jthis = $(othis);
            let id = jthis.text().trim();
            if (item.cache.hasOwnProperty(id)) {
                jthis.text(item.cache[id]);
                jthis.removeClass(item.class);
                othis.style = "";
            }
            else {
                path_params = {};
                path_params[item.path_key] = id;

                result = await preq(api_list[item.api_url], path_params, { method: "GET", }).then(get_json);
                console.log(item, item_index, result);
                let result_data = (item.result_key != "" ? result.json[item.result_key] : result.json);
                item.cache[id] = result_data;
                jthis.text(result_data);
                jthis.removeClass(item.class);
                othis.style = "";

            }
        }
    });
    localStorage.setItem("user_id_cache", JSON.stringify(user_id_cache));
    localStorage.setItem("task_id_cache", JSON.stringify(task_id_cache));
});
