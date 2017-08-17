$(function() {

	var cmax = 160,
		el = $('.page-meta-container [id^="id_syferadmin-meta-content_type-object_id-"][id$="-1-value"]').attr('maxlength', cmax);
	el.on('keypress keyup keydown', function () {
		$('#char_count').text(cmax - $(this).val().length);
	}).trigger('keyup');

	// Inline category filters
	// Converts filter text input into multiple checkboxes
	// and parses selections to filter string
	$('[data-filter]').each(function(){
		var $this = $(this),
			values = $(this).data('values'),
			value = $this.val(),
			item_id = $this.attr('id');

		// Create checkbox for each value
		$.each(values, function(key, value){
			var id = "filter-value-" + key;
			$('<input type=checkbox data-filter-value id="' + id + '-' + item_id + '" value="' + key + '"/> <label for="' + id + '-' + item_id + '">' + value + '</label>').appendTo($this.parent());
		});

		// Hide the text input
		$this.hide();

		// Convert current string value into selected checkboxes
		$this.parent().find('[data-filter-value][value=' + value.split('_or_').join('], [data-filter-value][value=') + ']').prop('checked', true);
	});

	// On filter checkbox change parse the
	$('body').on('change', '[data-filter-value]', function(){
		var input = $(this).parent().find('[data-filter]'),
			selected = $(this).parent().find('[data-filter-value]:checked');

		input.val(selected.map(function(){
			return $(this).val();
		}).get().join('_or_'));
	});

});