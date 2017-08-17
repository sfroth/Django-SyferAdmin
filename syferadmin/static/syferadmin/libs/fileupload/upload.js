$(function(){
	$('.file-upload + .file-upload__btn--edit').each(function(){
		$(this).prev().hide();
	});

	$('body').on('click', '.file-upload__btn--edit', function(e){
		e.preventDefault();
		$(this).prev().toggle();
	});

	$('body').on('click', '.file-upload__container input[type=checkbox][name$="-clear"]', function(e){
		var wrapper = $(this).closest('.file-upload__container');
			toggleFields = ['.file-upload__name', '.file-upload:visible', '.file-upload__btn--edit'];
		if($(this).is(':checked')) {
			if(confirm('Are you sure you want to clear the contents of this field?')) {
				for(var i=0; i<toggleFields.length; i++) {
					wrapper.find(toggleFields[i]).hide();
				}
			} else {
				e.preventDefault();
			}
		} else {
			for(var i=0; i<toggleFields.length; i++) {
				wrapper.find(toggleFields[i]).show();
			}
		}
	});
});