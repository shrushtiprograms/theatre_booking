frappe.listview_settings["Theatre Show"] = {
    onload(listview) {
        listview.filter_area.add([
            ["Theatre Show", "show_date", "=", frappe.datetime.get_today()],
        ]);
    },
};
