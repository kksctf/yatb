user_id_cache = JSON.parse(localStorage.getItem("user_id_cache")) || {};
task_id_cache = JSON.parse(localStorage.getItem("task_id_cache")) || {};
$("#flag_submit_form").submit(function (event) {
    event.preventDefault();
    //id = $(this).data("id");
    api_req(this, api_url['solve_task'], 'Solve flag', method = 'POST', ok_callback = (data) => {
        if (data.includes('-')) {
            var task = $("div[data-id=" + data + "]");
            task.addClass("solved");
            console.log("found task", task);
        }
    });
    //location.reload();
});
$(function () {
    const resolver_settings = [
        { class: "user_id_resolve", api_url: "get_user", result_key: "", cache: user_id_cache },
        { class: "task_id_resolve", api_url: "get_task", result_key: "task_name", cache: task_id_cache },
    ]
    resolver_settings.forEach(function (item) {
        $("." + item.class).each(function (index) {
            let jthis = $(this);
            let id = jthis.text().trim();
            if (item.cache.hasOwnProperty(id)) {
                jthis.text(item.cache[id]);
                jthis.removeClass(item.class);
                this.style = "";
            }
            else {
                api_req(undefined,
                    api_url[item.api_url].replace("None", id),
                    'Get uuid',
                    method = 'GET',
                    ok_callback = (result) => {
                        //result = JSON.parse(result);
                        let result_data = (item.result_key != "" ? result[item.result_key] : result);
                        item.cache[id] = result_data;
                        jthis.text(result_data);
                        jthis.removeClass(item.class);
                        this.style = "";
                    },
                    error_callback = (data) => { },
                    supress_ok = true,
                    async = false,
                );
            }
        });
    });
    localStorage.setItem("user_id_cache", JSON.stringify(user_id_cache));
    localStorage.setItem("task_id_cache", JSON.stringify(task_id_cache));
});
