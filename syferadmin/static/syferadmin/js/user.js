$(function(){

	// Cancel confirmation
	$('.downgrade').on('click', function() {
		if (!confirm("Really downgrade this staff member to customer?")) return false;
	});

});