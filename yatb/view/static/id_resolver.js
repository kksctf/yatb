const resolver_settings = [
    {
        class: "user_id_resolve",
        api_url: "api_users_get_username",
        path_key: "user_id",
        result_key: "",
        cache: {},
        cache_key: "user_id_cache"
    },
    {
        class: "task_id_resolve",
        api_url: "api_task_get",
        path_key: "task_id",
        result_key: "task_name",
        cache: {},
        cache_key: "task_id_cache"
    },
]

$(".flag_submit_form").submit(function (event) {
    event.preventDefault();

    req(api_list["api_task_submit_flag"], { data: getFormData(this), })
        .then(get_json)
        .then(ok_toast_generator("Solve flag"), nok_toast_generator("Solve flag"))
        .then((resp) => {
            console.log(resp);
            if (typeof (resp.json) == "string" && resp.json.includes('-')) {
                var task = $("div[data-id=" + resp.json + "]");
                task.addClass("solved");
                console.log("found task", task);
            }
        })
});

$(function () {
    resolver_settings.forEach(async function (item) {
        item.cache = JSON.parse(localStorage.getItem(item.cache_key)) || item.cache;

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
                try {
                    result = await preq(api_list[item.api_url], path_params, { method: "GET", }).then(get_json);
                    let result_data = (item.result_key != "" ? result.json[item.result_key] : result.json);
                    item.cache[id] = result_data;
                    jthis.text(result_data);
                    jthis.removeClass(item.class);
                    othis.style = "";
                } catch (err) {
                    console.error(item, path_params, err);
                }
            }
        }
        localStorage.setItem(item.cache_key, JSON.stringify(item.cache));
    });
});
