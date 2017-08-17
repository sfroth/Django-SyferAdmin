$(function () {

	$('.add-row a').on('click', initSelects);
	initSelects();

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

function initSelects() {
	$('select:visible:not([multiple]), inline-related:not(.empty-form) select:not([multiple])').chosen({ "disable_search_threshold" : 25 });
	$('select:visible[multiple], inline-related:not(.empty-form) select[multiple]').chosen({ "width": "100%" });
}