$(document).ready(function () {

	$('.add-row a').on('click', initMultipleSelects);
	initMultipleSelects();

	/**
	 * Have to override the Django default dissmissAddAnotherPopup to
	 * trigger chosen:updated on change
	 */
	var _dismissAddAnotherPopup = window.dismissAddAnotherPopup;
	window.dismissAddAnotherPopup = function(win, newId, newRepr) {
		var $el = $('#' + windowname_to_id(win.name));
		if (typeof _dismissAddAnotherPopup === 'function') {
			_dismissAddAnotherPopup(win, newId, newRepr);
		}
		if ($el.next('.chosen-container').length) {
			$el.trigger('chosen:updated');
		}
	};

});

function initMultipleSelects() {
	$('select[multiple]:visible').chosen();
}