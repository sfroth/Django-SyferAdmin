$(function () {

	// Make rows clickable on index
	$('.settings.index tr').on('click', function(e) {
		if ($(e.target).is('a')) {
			return true
		}
		window.location = $(this).find('a.edit').attr('href')
	});

});

