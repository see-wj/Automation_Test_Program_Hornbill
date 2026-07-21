"""GUI presentation helpers for instrument discovery results."""


def present_discovery_result(
    result,
    *,
    address_widgets,
    role_widgets=None,
    output_widget=None,
):
    widgets = tuple(address_widgets)
    configured_addresses = {
        widget: widget.currentText().strip()
        for widget in widgets
        if hasattr(widget, "currentText")
    }
    for widget in widgets:
        widget.clear()
    if output_widget is not None:
        output_widget.clear()

    for address, identity in zip(result.addresses, result.identities):
        display_address = str(address)
        if output_widget is not None:
            output_widget.append(f"{identity}  {display_address}")
        for widget in widgets:
            widget.addItem(display_address)

    for role, widget in (role_widgets or {}).items():
        address = configured_addresses.get(widget) or result.roles.get(role)
        if address not in result.addresses:
            address = result.roles.get(role)
        if address not in result.addresses:
            continue
        widget.setCurrentIndex(result.addresses.index(address))
