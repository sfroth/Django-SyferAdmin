$(document).ready(function () {

	// Nested sorting
	if($('.nested-sortable').length > 0){
		var list = $('.nested-sortable');
		if (list.prop('tagName') != 'OL') list = list.find('ol');
		options = {
			handle : 'div',
			items : 'li:not(.region)',
			maxLevels : list.data('depth'),
			placeholder : 'placeholder',
			distance: 5,
			forcePlaceholderSize: true,
			start: function(e, ui ){
			     ui.placeholder.height(ui.helper.outerHeight());
			},
			update : function(event, ui){
				$('.object-tools .sort').fadeIn();
			},
			cancel: 'li .code,li .code_display'
		};
		if (list.data('parent_id')) options['rootID'] = list.data('parent_id');
		list.nestedSortable(options);

		// Show expand categories
		$('body').on('click', '.expand', function(e) {
			$(this).toggleClass('open').closest('li').find('> ol').slideToggle();
		});
	}

	// Regular sorting
	if($('.sortable').length > 0) var list = $('.sortable');

	// Save items
	$('body').on('click', '.object-tools .sort', function(e) {
		var $this = $(this).addClass('loading');
		e.preventDefault();
		sortData = list.hasClass('nested-sortable') ? list.nestedSortable('toArray') : list.sortable('toArray');
		$.post('sort/', {json: JSON.stringify(sortData)}, function(data){
			data = $.parseJSON(data);
			if (data.success) flash(data.success);
			else flash(data.error ? data.error : 'Error: Sorting not saved!', "error");
			$this.removeClass('loading');
		});
	});

});