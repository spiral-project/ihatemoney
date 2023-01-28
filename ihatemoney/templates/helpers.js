function confirm_action(selector, { exclude_classes, add_classes } = { exclude_classes: "", add_classes: "" }) {
    const elements = $(selector)
    elements.each(function () {
        const element = $(this)
        let link = element.find('button')
        let deleteOriginalHTML = link.html()
        link.click(function () {
            if (link.hasClass("confirm")) {
                return true
            }
            link.html("{{_('Are you sure?')}}")
            link.removeClass(exclude_classes)
            link.addClass(`confirm btn-danger ${add_classes}`)
            return false
        })

        element.focusout(function () {
            link.removeClass(`confirm btn-danger ${add_classes}`)
            link.html(deleteOriginalHTML)
            link.addClass(exclude_classes)
        })
    })
}