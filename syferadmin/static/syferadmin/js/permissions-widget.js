$(function () {
	$('.permission-apps').each(function() { // @backies : Change back to $('.field-permissions').each after the markup is fixed
		var permissions = $(this)

		// Toggle groups permissions
		permissions.find('h5, h6').on('click', function(event) {
			toggle_group($(this).parent())

			// Toggle title: Enable all / Disable all
			if (event.target.nodeName === 'H5') {
				var heading = $(this), title = (heading.parent().hasClass('active')) ? 'Disable all' : 'Enable all'
				heading.attr('title', title)
			}
		})

		// Keep track of active states when toggling checkboxes
		permissions.find('input').on('change', function() {
			var input = $(this)
			check_state(input.closest('.permission-items').parent())
			check_state(input.closest('.permission-types').parent())
			// Active class on parent <li>
			if (input.is(':checked')) input.parent('li').addClass('active')
			else input.parent('li').removeClass('active')
		})

		// Toggle groups permissions
		permissions.on('click', '.group-toggle', function(e) {
			$(this).parent().toggleClass('active-toggle').find('.permission-types').slideToggle(250).parent().siblings().removeClass('active-toggle').find('.permission-types').hide()
			// Toggle title
			var buttontitle = ($(this).closest('.active-toggle').length > 0) ? 'Hide group' : 'Show group'
			$(this).attr('title', buttontitle)
		})

		permissions.find('input').trigger('change')
	})
})

// Check checkbox states and determine active state for group
function check_state(group) {
	if (group.find('input:checked').length > 0) group.addClass('partial')
	else group.removeClass('partial')
	if (group.find('input:checked').length == group.find('input').length) group.addClass('active').removeClass('partial')
	else group.removeClass('active')
}

// Toggle group on or off depending on active state
function toggle_group(group) {
	group.find('input').prop('checked', !group.hasClass('active')).trigger('change')
}