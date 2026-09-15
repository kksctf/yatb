function load_all_dynamic_info() {
    tasks = $(".dynamic_task_info_field").map((idx, info_field) => {
        return info_field.dataset.id;
    }).get();

    req(api_list["api_dynamic_task_infos"], { data: { "tasks": tasks } })
        .then(get_json)
        .then((data) => { return data; }, nok_toast_generator("Get dynamic task info"))
        .then((data) => {
            Object.entries(data.json.data).forEach(([task_id, info]) => {
                set_status(task_id, info);
            });
        });
};

function set_status(task_id, info) {
    $("#data-" + task_id).html(info);
    if ("macy" in window) {
        updateMacy();
    }
}

$(".dynamic_task_info").click(function (event) {
    event.preventDefault();
    let task_id = this.dataset.id;
    preq(api_list["api_dynamic_task_info"], { "task_id": task_id }, { method: 'GET' })
        .then(get_text)
        .then((data) => { return data; }, nok_toast_generator("Get dynamic task info"))
        .then((data) => {
            set_status(task_id, data.text);
        });
});

$(".dynamic_task_start").click(function (event) {
    event.preventDefault();
    let task_id = this.dataset.id;


    set_status(task_id, "Task building in process")

    preq(api_list["api_dynamic_task_start"], { "task_id": task_id }, { method: 'GET' })
        .then(get_text)
        .then(ok_toast_generator("Start dynamic task"), nok_toast_generator("Start dynamic task"))
        .then((data) => {
            set_status(task_id, data.text);
        });
});

$(".dynamic_task_stop").click(function (event) {
    event.preventDefault();
    let task_id = this.dataset.id;
    preq(api_list["api_dynamic_task_stop"], { "task_id": task_id }, { method: 'GET' })
        .then(get_text)
        .then(ok_toast_generator("Stop dynamic task"), nok_toast_generator("Stop dynamic task"))
        .then((data) => {
            set_status(task_id, data.text);
        });
});

$(".dynamic_task_restart").click(function (event) {
    event.preventDefault();
    let task_id = this.dataset.id;
    preq(api_list["api_dynamic_task_restart"], { "task_id": task_id }, { method: 'GET' })
        .then(get_text)
        .then(ok_toast_generator("Restart dynamic task"), nok_toast_generator("Restart dynamic task"))
        .then((data) => {
            set_status(task_id, data.text);
        });
});

$(".dynamic_task_extend").click(function (event) {
    event.preventDefault();
    let task_id = this.dataset.id;
    preq(api_list["api_dynamic_task_extend"], { "task_id": task_id }, { method: 'GET' })
        .then(get_text)
        .then(ok_toast_generator("Extend dynamic task"), nok_toast_generator("Extend dynamic task"))
        .then((data) => {
            set_status(task_id, data.text);
        });
});
