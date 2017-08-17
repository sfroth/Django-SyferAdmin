$("html").removeClass("no-js");

window.fancyboxOptions = {
	padding: 0,
	margin: 0,
	minWidth: '100%',
	minHeight: '100%'
}

$(window).load(function() {
	$('body').removeClass('loading');
})

$(document).ready(function() {
	Overlay.init();

	// Settings page - update 'Google_Plus' to read 'Google Plus'
	if ($('body').is('.settings.edit')) {
		$('input[name="Company.Social.Google_Plus.show"]').closest('section').find('h3').text('Google Plus');
	}

	// Update the overlay image when hovering the link
	$('.zoom').hover(function(e) {
		var img = new Image(),
			link = $(this),
			imgSrc = link.attr('href');
		img.src = imgSrc;
		var imgWidth = img.width,
			imgHeight = img.height;

		var overlay = $('.overlay-container'),
			_overlayMaxed = (overlay.width() >= $(window).width()) ? true : false,
			_imageWiderThanScreen = (imgWidth > $(window).width()) ? true : false;

		overlay.removeClass('overlay-container--help').addClass('overlay-container--image')
		$('.overlay-content').html('<a href=' + imgSrc + ' class="overlay-container--image-link">(Full Size: ' + imgWidth + 'x' + imgHeight + ')</a>');
		$('.overlay-title').text('Image Viewer');
		$('.overlay-container--image-link').prepend(img);
		var newImg = $('body').find('.overlay-content img');
		var imgLink = $('body').find('.overlay-container--image-link');

		// Only make the image zoomable if its wider than the overlay
		if (imgWidth > overlay.width() - 50 && !_overlayMaxed) {
			img.title = 'View full size: ' + imgWidth + 'x' + imgHeight;
			// newImg.after('<data-content','bar');
			imgLink.addClass('zoomable');
		}

		imgLink.on('click', function(e) {
			e.preventDefault();

			// if the overlay is equal to width of screen then do nothing
			if (_overlayMaxed) return true;

			var img = $(this).find('img');

			if (imgLink.hasClass('zoomable')) {
				overlay.css({'max-width': imgWidth + 50}) // 25px padding on left and right of image
				setTimeout(function() {
					img.attr('title', 'Zoom out');
					imgLink.removeClass('zoomable').addClass('zoomed');
					// if (_imageWiderThanScreen) {
					// 	img.css({'max-width': 'none'})
					// 	$('.overlay-content-wrapper').css({'overflow': 'auto'})
					// }
				}, 500);
			}
			if (imgLink.hasClass('zoomed')) {
				overlay.removeAttr('style');
				// img.removeAttr('style')
				setTimeout(function() {
					img.attr('title', 'View Full Size: ' + imgWidth + 'x' + imgHeight);
					imgLink.removeClass('zoomed').addClass('zoomable');
				}, 500);
			}
		});
	});

	$('.file-zoom').on('mouseenter', function(){
		var img = new Image(),
			link = $(this),
			imgSrc = link.parent().find('img').attr('src');
		img.src = imgSrc;

		var imgWidth = img.width,
			imgHeight = img.height;

		var overlay = $('.overlay-container'),
			_overlayMaxed = (overlay.width() >= $(window).width()) ? true : false,
			_imageWiderThanScreen = (imgWidth > $(window).width()) ? true : false;

		overlay.removeClass('overlay-container--help').addClass('overlay-container--image')
		$('.overlay-content').html('<a href=' + link.attr('href') + ' class="overlay-container--image-link" download="' + $('#id_name').val() + '">(Download File)</a>');
		$('.overlay-title').text('File Viewer');
		$('.overlay-container--image-link').prepend(img);
	});

	// Show the image overlay
	$('body').on('click', 'a.zoom, a.file-zoom', function(e) {
		e.preventDefault();

		setTimeout(function() {
			// Show the overlay by adding class to html
			$('html').addClass("overlay-active");
		}, 200);
	})

	$('body').on('click', '.overlay-title', function(e) {
		$('html').removeClass('overlay-active');
	})

	// Close overlay with escape key
	$(document).keydown(function(e) {
		switch(e.which) {

			// Esc key closes overlay
			case 27: $('html').removeClass('overlay-active'); break
		}
	})

	// Make sure the dropdown works on touch
	$("#user-tools.dropdown > a").on('click', function(e) {
		if (Modernizr.touch) {
			e.preventDefault();
		}
	})

	// Fancy side menu
	var $nav = $('body > nav'),
		$navClose = $nav.find(".close");
		$menuBtn = $('.menu-toggle');

	// Toggle menu
	$('.menu-toggle').on('click', function() {
		// $nav.toggleClass('open');
		$('html').toggleClass('nav-open');
		$(this).blur();
	});

	// close the menu with the close button
	$navClose.click(function() {
		$('.menu-toggle').trigger("click");
		$(this).closest(".highlight").removeClass("highlight");
	});

	// Data-toggles
	$('body').on('click', '[data-toggle-item]', toggleItem);

	// Save button dropdowns
	$('.save-group [data-toggle]').on('click', function(e) {
		e.preventDefault();
		e.stopPropagation();
		$(this).closest('.save-group').find('.' + $(this).data('toggle')).toggle().toggleClass('open');
	});
	$('html').on('click', function() {
		$('.save-group .open').hide().removeClass('open');
	});

	// Double save prevention
	$('form').on('submit', function(e) {
		var saveButtons = $(this).find('[data-save-group] button');

		// Ignore additional submits
		if (saveButtons.is('.loading')) {
			return false;
		}

		if (saveButtons.length) {
			saveButtons.addClass('loading');
		}
	});

	// Prevent double submitting the changelist actions menu
	$('body').on('submit', '#changelist-form', function(){
		var form = $(this),
			submits = form.find(':submit');

		if(submits.first().is('.loading')) {
			return false;
		}
		submits.removeClass('button').addClass('btn loading');
	});

	// MENU AIM (Mouse move detection)
	if($.fn.menuAim) {
		$('body > nav > ul').menuAim({
			activate: function(row) {
				$(row).addClass('highlight');
			},
			deactivate: function(row) {
				$(row).removeClass('highlight');
			}
		});
	}

	// Accordion slidetoggle
	$("form").on("click", "[data-slide-toggle]", function() {
		var toggleData = $(this).data("slide-toggle"), container = $(this).closest(":has(" + toggleData + ")"), target = container.find(toggleData);

		// toggle active class on button & slideToggle this hidden element
		$(this).toggleClass("active").closest(container).toggleClass("active-toggle").find(toggleData).slideToggle(600);

		return false;
	});

	// Raise hit area for unopened slide toggle fieldsets
	$('form').on("click", "fieldset:not(.active-toggle)", function(e) {
		$(this).find("> [data-slide-toggle]").trigger('click');
	});

	/*
		Inline Forms
	*/

	// Deletion of stacked inline formsets
	$('body').on('click', '.inline-related [data-action=remove]', function() {
		inline = $(this).parent();
		inline.find('.field-DELETE input, [data-container=delete] input').prop('checked', true);
		inline.slideUp();
	});

	/*
		Form popups
	*/

	// close popup on cancel
	$('body.form').on('click', 'input[name="_popup"] ~ .submit-row .btn.cancel', function() {
		window.close();
	});

	// Selects
	if ($.fn.chosen != undefined) {
		$('.add-row a').on('click', initSelects);
		$('#action-toggle').on('click', initSelects);
		$('body').on('click', '#log .add', initSelects);
		initSelects();
	}

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

	// Strip out hex when pasting a color into input
	$('#id_background_color').on('paste', function(e){
		var text = (e.originalEvent || e).clipboardData.getData('text/plain') || false;
		if(text) {
			text = text.replace('#', '');
			$(this).val(text);
			return false;
		}
	});

	/*
	 * 	Filters
	 */
	$('.filterer').on('change', function() {
		window.location = [location.protocol, '//', location.host, location.pathname, $(this).find('option:selected').val()].join('');
	});
	if ($('input.filter-box').length > 0) {
		$('input.filter-box').each(function() {
			$(this).closest('form').find('input[type=submit]').show();
		});
	}

	if($('#changelist-filter > h2').length > 0) {
		$('body').on('click', '#changelist-filter > h2', function(e) {
			$(this).parent().toggleClass("active");
			e.stopPropagation();
		}).on('click', '#changelist-filter', function(e){
			e.stopPropagation();
		});
		$('html').on('click', function(e){
			$('#changelist-filter').toggleClass("active", false);
		}).on('keydown', function(e){
			if(e.which === 27) {
				$('#changelist-filter').toggleClass("active", false);
			}
		});

	}

	initKeyboardShortcuts();
	initDisableDoubleSubmission();

	/*
	 * Admin import/export format selector
	 */
	$('#id_import_file').on('change', function(){
		var val = $(this).val().match(/\.([a-zA-Z]+)$/),
			opts = {};
		if(val && $('#id_input_format').length > 0) {
			val = val[1].toLowerCase();

			$('#id_input_format option').each(function(){
				opts[$(this).text()] = $(this).val();
			});

			if(val in opts) {
				$('#id_input_format').val(opts[val]);
				$('#id_input_format').trigger('chosen:updated');
			}
		}
	});

	/*
	 *  Make the name field clickable to edit on sortable pages
	 */
	if($('.nested-sortable').length > 0) {
		$('.nested-sortable').find('li > div').each(function(){
			var edit = $(this).find('.list_actions a.edit'),
				name = $(this).find('strong.name');

			if(edit.length > 0 && name.length > 0 && name.find('a').length === 0) {
				name.html($('<a></a>').attr('href', edit.attr('href')).attr('title', 'Edit this record').text(name.text()));
			}
		});
	}

	/*
	 * Iframe popups for adding related items
	 * @anthony, uncomment this below
	 */
	// $('.add-another').on('click', function(e){
	// 	return showAddAnotherIframe(this);
	// }).each(function(){
	// 	// Remove the onclick attribute since you can't override it from straight JS
	// 	$(this).attr('oldclick', $(this).attr('onclick'));
	// 	$(this).removeAttr('onclick');
	// });

	$('.popup .btn.cancel').on('click', function(e){
		// Close the iframe when clicking cancel inside of it
		parent.dismissAddRelatedObjectIframe(window);
		return false;
	});

	// Hide the select all action controls on load
	$('#changelist-form .question, #changelist-form .all, #changelist-form .clear').hide();

	// Localization js

	$('.translate-options input').on('change', function(){
		var self = $(this),
		lang = self.data('id').replace('-','_'),
		set_languages = $.cookie('language') ? $.cookie('language').split(',') : [];
		$('.trans-field').filter('[class$=' + lang + ']').slideToggle();
		if(self.is(':checked') && $.inArray(lang, set_languages) < 0){
			$('body').addClass('trans-active');
			set_languages.push(lang);
			$.cookie('language', set_languages.join(','), { expires: 7 });
		} else {
			$('body').removeClass('trans-active');
			set_languages.splice( $.inArray(lang, set_languages), 1 )
			$.cookie('language', set_languages.join(','), { expires: 7 });
		}
	});
	// Auto show language fields for cookie
	if($.cookie && $.cookie('language')){
		var language = $.cookie('language').split(',');
		if(language.length > 0){
			$('html').addClass('trans-active');
		}
		$.each(language, function(index, lang){
			$('.trans-field').filter('[class$=' + lang + ']').show();
			$('.translate-options input#lang-' + lang.replace('_', '-')).prop('checked', true);
		});
	}

	$('.map').on('click', function(e){
		var $this = $(this);
		if(typeof google === "undefined") {
			// Google Maps doesn't like async loading of this library, so we use their callback for the first call
			// and set the element to the body as a global attr so we have access to it. Not great but best I could find
			$('body').data('mapElement', $this);
			$.getScript('https://maps.googleapis.com/maps/api/js?sensor=false&callback=clickMap');
		} else {
			clickMap($this);
		}
		return false;
	});

	// Used On trigger in blocks/mantles
	$('a.used-on').on('click', function(e){
		var usedon = $('div.used-on')
		Overlay.trigger(usedon.data('title'), usedon.html());
	});

	// Fix help on inline table headings
	$('img.help-tooltip').attr('src', 'javascript:void(0)').each(function(){
		$(this).attr('data-content', $(this).attr('title'));
	}).on('click', function(e){
		var $this = $(this);
		Overlay.trigger($.trim($this.parent().text()), $this.attr('title'));
	});

});

// Custom selects
function initSelects() {
	// No custom selects on touch devices
	if (!$('html').is('.no-touch')) return false;

	// Chosen and Chosen Sortable required
	if ($.fn.chosen == undefined || $.fn.chosenSortable == undefined) return false;

	var multiple_selects = 'select:visible[multiple], .dynamic-variation_set:not(.empty-form) select[multiple]',
		single_selects = 'select:visible:not([multiple]), .dynamic-variation_set:not(.empty-form) select:not([multiple])'

	// Disable read only fields
	$('select').each(function() {
		if ($(this).attr('readonly')) {
			$(this).data('was-disabled', $(this).is(':disabled')).attr('disabled', 'disabled');
		}
	});

	// Multiple selects
	$(multiple_selects)
		.not('.initialized')
		.chosen({ "width": "100%" })
		.chosenSortable()
		.addClass('initialized');
		// .parent().find('.help').hide();

	// Single selects
	$(single_selects)
		.not('.initialized, .filterer')
		.chosen({ "disable_search_threshold" : 25 })
		.chosenSortable()
		.addClass('initialized');

	// Re-enable read only fields
	$('select').each(function() {
		if ($(this).attr('readonly')) {
			if (!$(this).data('was-disabled')) $(this).attr('disabled', false);
		}
	});
}

// Check method safe for CSRF
function csrfSafeMethod(method) {
	// these HTTP methods do not require CSRF protection
	return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

// Easy flash notifications
function flash(message, group) {
	group = group || "success";
	if (!$('[data-main-messages]').length) $('main').prepend('<ul class="messages" style="display: none;"></ul>');
	$li = $('<li></li>').addClass(group).html(message);
	$('.messages').empty().append($li).stop().slideDown().delay(2500).slideUp();
}

// Get cookie
function getCookie(name) {
	var cookieValue = null;
	if (document.cookie && document.cookie != '') {
		var cookies = document.cookie.split(';');
		for (var i = 0; i < cookies.length; i++) {
			var cookie = jQuery.trim(cookies[i]);
			// Does this cookie string begin with the name we want?
			if (cookie.substring(0, name.length + 1) == (name + '=')) {
				cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
				break;
			}
		}
	}
	return cookieValue;
}

jQuery.fn.disableDoubleSubmission = function(){
	var last;
	$(this).bind('submit', function(e){
		var elapsed = 50000;
		if(last) {
			elapsed = e.timeStamp - last;
		}

		last = e.timeStamp;

		if(elapsed < 800) {
			return false;
		}
		return true;
	});
}

function initDisableDoubleSubmission() {
	$('form').disableDoubleSubmission();
}

function initKeyboardShortcuts() {
	/*
	 * Keyboard shortcuts to save
	 */
	var isMac = !!navigator.platform.match(/^Mac/);
		metaLabel = isMac ? '⌘' : 'ctrl';

	$(window).on('keydown', function(e){
		// Capture +enter to save form fields
		if(e.which === 13) {
			var meta = isMac ? e.metaKey : e.ctrlKey,
				save = meta && $('[name="_save"]').length > 0,
				savecontinue = save && e.shiftKey,
				savenew = save && e.altKey;

			if (!$('body').hasClass('fancybox-lock')) {
				if(savenew) {
					$('[name="_addanother"]').first().trigger('click');
				} else if(savecontinue) {
					$('[name="_continue"]').first().trigger('click');
				} else if(save) {
					$('[name="_save"]').first().trigger('click');
				}
			}
		// forward slash focuses the search input field
		} else if(e.which === 191 && !$(e.target).is(':input,label')) {
			$('#changelist-search #searchbar').focus();
			return false;
		}
	});

	// Add titles to fields showing the shortcuts
	$('[name="_save"]').attr('title', '(' + metaLabel + '+enter)');
	$('[name="_continue"]').attr('title', '(' + metaLabel + '+shift+enter)');
	$('[name="_addanother"]').attr('title', '(' + metaLabel + '+alt+enter)');
}

// Set up default jQuery AJAX settings
$.ajaxSetup({
	beforeSend: function(xhr, settings) {
		if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
			xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
		}
	}
});

// Easy delay method
var delay = (function(){
	var timer = 0;
	return function(callback, ms){
		clearTimeout (timer);
		timer = setTimeout(callback, ms);
	};
})();

function toggleItem(e) {
	var e = $(e.target);

	if (e.data("toggle-max-width") && $(window).width() >= e.data("toggle-max-width")) return true;

	var toggleData = e.data("toggle-item"), container = e.closest(":has("+toggleData+")");

	// Close siblings
	if (e.data("toggle-siblings")) {
		var siblings = e.closest(e.data("toggle-siblings")).siblings().find(toggleData);
		siblings.slideUp().closest(".active-toggle").removeClass("active-toggle");
	}

	// Toggle element
	e.closest(container).toggleClass("active-toggle").find(toggleData).slideToggle(300);

 	return false;
}

// Get text of node without children's text
// http://stackoverflow.com/questions/11362085/jquery-get-text-for-element-without-children-text
jQuery.fn.justtext = function() {

    return $(this).clone()
            .children()
            .remove()
            .end()
            .text();

}

var Overlay = {
	/**
	* Help Modal
    */

	init: function(settings) {
		this.build();
		this.active = $();
		this.nextItem = $();
		this.prevItem = $();
		this.containerClass = '.form-group';
		this.container = $();
		this.bindControls();
	},

	// Create the overlay markup if it doesn't exist
	build: function() {
		var self = this;

		if (!$(".overlay-container").length > 0) {
			$('body').append(
				'<div class="overlay-container overlay-container--help">' +
					'<div class="overlay-container-wrapper">' +
						'<button class="overlay-title" type="button"></button>' +
						'<div class="overlay-content-wrapper">' +
							'<div class="overlay-content"></div>' +
						'</div>' +
					'</div>' +
				'</div>' +
				'<button class="overlay-close" type="button" title="Close Overlay"></button>'
			)
		}
	},

	// Bind Controls
	bindControls: function() {
		var self = this;

		// --- UPDATE --- //
		$(document).on('mouseenter', 'span.help', function(e) {
			self.update($(this));
		})

		// --- CLOSE --- //
		$('body').on('click', 'button.overlay-title, .overlay-close', function(e) {
			self.close();
		})

		// --- OPEN --- //
		$('body').on('click', 'span.help', function(e) {
			self.open($(this));
			e.preventDefault();
		})

		// Close overlay with escape key
		$(document).keydown(function(e) {
			switch(e.which) {
				// Left arrow key moves to previous help item
				case 37: self.prev(); break

				// Right arrow key moves to next help item
				case 39: self.next(); break

				// Esc key closes overlay
				case 27: self.close(); break
			}
		})
	},

	next: function(element) {
		var self = this
			nextContainer = self.container.next(self.containerClass),
			nextItem = self.container.nextAll(self.containerClass).find('.help').first();

		if (nextItem.length > 0 && $('.overlay-container').hasClass('overlay-container--help')) {
			// Update the next item
			self.update(nextItem);

			// Update active class on icon
			$('.help').removeClass('active');
			nextItem.addClass('active');
		}
	},

	prev: function(element) {
		var self = this
			prevContainer = self.container.prev(self.containerClass),
			prevItem = self.container.prevAll(self.containerClass).find('.help').last();

		if (prevItem.length > 0 && $('.overlay-container').hasClass('overlay-container--help')) {
			// Update the previous item
			self.update(prevItem);

			// Update active class on icon
			$('.help').removeClass('active');
			prevItem.addClass('active');
		}
	},

	// Update overlay:
	// Swap out title and content
	update: function(element, title, content) {
		var self = this,
			overlayContent = $('.overlay-content'),
			overlayTitle = $('.overlay-title'),
			btn = element;

		// TEMP:
		$('.overlay-container').removeClass('overlay-container--image').addClass('overlay-container--help').removeAttr('style')

		self.active = btn;
		self.active = element;
		self.container = btn.closest(self.containerClass);

		console && console.log(btn.data('content'));

		// Update the content in overlay
		overlayTitle.text(btn.closest('label').justtext());
		overlayContent.text(btn.data('content'));
	},

	// Close overlay
	close: function() {
		// TEMP:
		$('.overlay-container').removeAttr('style'); // max-width

		$('html').removeClass("overlay-active");
		$('.help').removeClass('active');
	},

	// Open overlay
	open: function(element) {
		// Remove active class from other help items
		$('.help').removeClass('active');

		// Set active class on this help item
		$(element).addClass('active');

		// Show the overlay by adding class to html
		$('html').addClass("overlay-active");
	},

	trigger: function(title, content) {
		$('.overlay-title').text(title);
		$('.overlay-content').empty().append(content);
		this.open($());
	}
}

/*
 * Iframe popups window functions. These need to stay here.
 */
function showAddAnotherIframe(el) {
	// Markup for the popups
	var el = $(el),
		href = el.attr('href'),
		id = +new Date(),
		wrapper = $('<section id="popup-' + id + '" class="popup-wrapper"><a href="#" class="popup-close">Close</a></section>');
		iframe = $('<iframe name="popup-' + id + '" src="" class="addanother"></iframe>');

	iframe.attr('src', href + (href.indexOf('?') >= 0 ? '&' : '?') + '_popup=1');
	wrapper.data('dismiss', function(value, text){
		// If value and text are empty we are just closing the iframe
		if(value !== undefined && text !== undefined) {
			// @todo: Make this work with more than just select elements
			var id = el.attr('id').replace(/^add_/, ''),
				option = $('<option value="' + value + '">' + text + '</option>');
			option.prop('selected', true);
			$('#' + id + ', #' + id + '_from, #' + id + '_to').append(option).trigger('change').trigger('chosen:updated');
		}

		wrapper.remove();
	});
	// close button
	wrapper.find('.popup-close').on('click', function(e){
		wrapper.remove();
	});
	wrapper.append(iframe);
	$('body').append(wrapper);
	return false;
}

function dismissAddRelatedObjectIframe(win, value, text) {
	// Populate the dropdown and close the iframe
	$('#' + win.name).data('dismiss')(value, text);
}

function clickMap(el) {
	// Google maps doesn't like async mode, see .map click event for more on why this is
	if(typeof el === "undefined") {
		el = $('body').data('mapElement');
	}
	// if(!el.is('[href*=maps]')) {
	// 	mapIPAddress(el);
	// 	return false;
	// }
	var content = el.closest('[itemprop="address"]').clone();
	content.find('a').remove();
	mapAddress(el, content.html());
}

function mapPopup(position, link, title, content, zoom) {
	var id = 'map' + (+new Date());
	var el = $('<div id="map" style="width: 100%; height: ' + ($(window).height() * 0.65) + 'px; min-height: 250px;"></div>');
	Overlay.trigger(title, el);
	el.after(link.clone().removeClass('map').text('Full Map'));
	var position = new google.maps.LatLng(position[0], position[1]);
	var map = new google.maps.Map(el.get(0), {
		zoom: (typeof zoom === "undefined" ? 10 : zoom),
		center: position,
		mapTypeControlOptions: {
			position: google.maps.ControlPosition.LEFT_BOTTOM,
			style: google.maps.MapTypeControlStyle.HORIZONTAL_BAR,
			mapTypeIds: [
				google.maps.MapTypeId.ROADMAP,
				google.maps.MapTypeId.SATELLITE
			]
		}
	});

	var marker = new google.maps.Marker({
		position: position,
		map: map,
		title: title
	});

	var infowindow = new google.maps.InfoWindow({
		content: content
	});
	infowindow.open(map, marker);
}

// function mapIPAddress(el) {
// 	var ip = el.data('address');
// 	// Get GEO IP
// 	$.getJSON('/api/ip/' + ip + '/', function(data){
// 		// Add as a map
// 		var title = data['ip'] + " - " + data['hostname'],
// 			content = "<h3>" + data['ip'] + " - " + data['hostname'] + "</h3><p><dl>";
// 		$.each(['postal_code', 'city', 'region', 'country_name'], function(){
// 			if(_.has(data, this) && data[this] !== null) {
// 				content += "<dt>" + this.replace(/_.*/, '') + "</dt><dd>" + data[this] + "</dd>";
// 			}
// 		});
// 		content += "</dl>";
// 		mapPopup([data['latitude'], data['longitude']], el, title, content, 10);
// 	}).fail(function(){
// 		alert('That does not appear to be a valid public IP Address');
// 	});
// }

function mapAddress(el, content) {
	var address = el.data('address');
	var geocoder = new google.maps.Geocoder();
	geocoder.geocode({'address': address}, function(results, status) {
		if (status === google.maps.GeocoderStatus.OK) {
			var location = [results[0].geometry.location.lat(), results[0].geometry.location.lng()];
			mapPopup(location, el, address, content, 17);
		} else {
			alert('Geocode was not successful for the following reason: ' + status);
		}
	});
}
