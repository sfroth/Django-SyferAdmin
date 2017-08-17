$(function() {

	// Pagination
	var items = 10,
		note = $('.releasenote'),
		total = note.length,
		pages = Math.ceil(total / items),
		lastPageItems = total % items

	// Hide everything past the first 'page' of items
	$('.releasenote:eq('+ (items - 1) +') ~ .releasenote').hide()

	// Create the pagination markup:
	if (note.eq(items).length > 0) {
		$('.releasenotes-list').after(
			'<div class="releasenotes-pagination" data-page="1">' +
				'<div class="releasenotes-counter">' +
					'<p>Showing <span class="releasenotes-count">' + items + '</span> of <span class="releasenotes-pages">' + total + '</span></p>' +
					'<button type="button" class="load-all btn-reset" data-load-all-items>View All</button>' +
				'</div>' +
				'<button type="button" class="load-more" data-load-items='+ items +'>Load More</button>' +
			'</div>'
		)
	}

	hideButtons = function() {
		$('.releasenotes-pagination button').addClass('hidden')
	}

	$('body').on('click', '[data-load-items]', function() {
		var pagination = $('.releasenotes-pagination'),
			count = parseFloat($('.releasenotes-count').text()),
			page = parseFloat(pagination.attr('data-page'))

		console.log('count: ' + count)

		// Load the next 'page' of items:
		$('.releasenotes-list li:visible:last').nextAll(':lt('+ $(this).data('load-items') +')').fadeIn(function() {

			// update the counter:
			var newCount = (pages - page == 1) ? count + lastPageItems : count + items
			$('.releasenotes-count').text(newCount)

			// If were on the last page hide buttons
			if (pages - page == 1) {
				hideButtons()
			}

			// update the page data
			pagination.attr('data-page', page + 1)
		})
	})

	$('body').on('click', '[data-load-all-items]', function() {
		// Update the counter:
		$('.releasenotes-count').text(total)

		// Fade in all the items
		$('.releasenote').fadeIn(function() {
			hideButtons()
		})
	})
})