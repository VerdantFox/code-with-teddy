function pushNotify(title, text = "", status = "success", autotimeout = 3000) {
  new Notify({
    status: status,
    title: title,
    text: text,
    effect: "fade",
    speed: 500,
    customClass: "",
    customIcon: "",
    showIcon: true,
    showCloseButton: true,
    autoclose: true,
    autotimeout: autotimeout,
    gap: 20,
    distance: 20,
    type: 1,
    position: "right bottom",
  })
}
