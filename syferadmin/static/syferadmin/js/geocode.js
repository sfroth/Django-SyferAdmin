function initMap() {
	var el = $('.geo__map'),
		map = new google.maps.Map(el.get(0), {
			zoom: 3,
			center: {lat: 37.755, lng: -95.362},
			scrollwheel: false
		}),
		marker = new google.maps.Marker({'map': map, 'draggable': true});

	if($('[name=latitude]').val() != '') {
		marker.setPosition({lat: parseFloat($('[name=latitude]').val()), lng: parseFloat($('[name=longitude]').val())});
		map.setCenter(marker.getPosition());
		map.setZoom(17);
	}

	el.data('map', map);
	el.data('geocoder', new google.maps.Geocoder());
	el.data('marker', marker);

	google.maps.event.addListener(marker, 'drag', function (event) {
		setCoords(this);
	});
	google.maps.event.addListener(marker, 'dragend', function (event) {
		map.panTo(this.getPosition());
	});

	$(window).on('resize', function(e){
		map.panTo(marker.getPosition());
	});
}

function geocodeAddress(el, address) {
	var map = el.data('map'),
		marker = el.data('marker'),
		geocoder = el.data('geocoder');

	geocoder.geocode({'address': address}, function(results, status) {
		if (status === 'OK') {
			marker.setPosition(results[0].geometry.location);
			map.setCenter(marker.getPosition());
			map.setZoom(17);
			setCoords(marker);
			$('.geo__message').html('')
			$('.geo__message-wrapper').hide();
		} else {
			$('.geo__message').html('Unable to find coordinates for <strong>"' + address + '"</strong>');
			$('.geo__message-wrapper').show();
		}
	});
}

function setCoords(marker) {
	$('[name=latitude]').val(marker.getPosition().lat().toFixed(6));
	$('[name=longitude]').val(marker.getPosition().lng().toFixed(6));
}

$(function(){
	var fieldset = $('[name=address]').closest('fieldset').addClass('geo__container'),
		fields = ['address', 'city', 'postal_code', 'country'];

	fieldset.find('.form-group.field-latitude').before('<div class="geo"><div class="geo__map"></div><div class="geo__message-wrapper"><p class="geo__message"></p></div></div>');

	fieldset.on('change', function(e){
		if($.map(fields, function(v){ if($('[name="' + v + '"]').val() != ''){ return true}}).length == fields.length) {
			var address = $.map(fields, function(v){
				var $this = $('[name="' + v + '"]');
				return $this.is('select') ? $this.find('option:selected').text() : $this.val();
			}).join(', ');
			geocodeAddress($('.geo__map'), address);
		}
	});

	initMap();
});