// Set javascript datepickers for browsers that don't support date types
$(document).ready(function () {

	var e = document.createElement('input');
	e.setAttribute('type', 'datetime-local');

	if (e.type == 'text') {
		$('[type^=datetime]').datetimepicker();
		$('[type=date]').datepicker({dateFormat: 'yy-mm-dd'});
	}

	$('body').on('click', '[data-form-clear]', function(e){
		e.preventDefault();
		var form = $(this).closest('form');

		form.find('input').not('[type=submit], [type=hidden]').val('');
		form.submit()
	});

});