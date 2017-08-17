function libraryReIndex(el) {
	var order = $(el).find(':input[name$=sort]');
	order.each(function(index){
		// Only update of the dropdown field has a value
		if($(this).closest('li').find('select').val().length > 0) {
			$(this).val(index);
		} else {
			$(this).val("");
		}
	});
}

function initLibrarySelectSortable() {
	$(':input[name$=sort]').closest('ol,ul').sortable({
		cancel: 'a,:input,label',
		cursor: 'move',
		containment: 'parent',
		forcePlaceholderSize: true,
		items: '> li',
		placeholder: 'placeholder',
		tolerance: 'pointer',
		// After sorting finishes change the sort field to a number
		stop: function(){
			libraryReIndex(this);
		}
	});

	$('body').on('click', '.ui-sortable .delete', function(e){
		if(confirm('Are you sure you want to remove this item?')) {
			$(this).closest('li').fadeOut();
			$('#' + $(this).find('label').attr('for')).prop('checked', true);
		}
		e.preventDefault();
	}).on('click', '.add-row', function(e){
		$('.ui-sortable').each(function(){
			libraryReIndex(this);
			$(this).sortable('refresh');
		});
	}).on('change', 'select', function(e){
		$('.ui-sortable').each(function(){
			libraryReIndex(this);
		});
	});
}

$(function(){
	initLibrarySelectSortable();
});