$(function(){

	// Open item browser
	$('.related.items').on('click', '[data-action=add-item]', function() {
		container = $(this).parent()
		itemBrowser.init($(this).data('content-type-id'))
		itemBrowser.triggerElement = $(this)
		itemBrowser.target = container
		itemBrowser.exclude = _.map(container.find('li:visible [name$="related_object_id"]'), function(item) { return item.value })
		itemBrowser.open()
	// Delete items
	}).on('click', '[data-action=delete]', function() {
		var _delete = $(this).closest('li').find('[name$="DELETE"]');

		// Either hide and setup for deletion or remove
		if (!confirm('Are you sure you want to remove this related item?')) return
			_delete.attr('checked', true);
			$(this).closest('li').fadeOut(function(e) {
				if (!_delete.length) $(this).remove()
			})
	// Adding of extra field information
	}).on('change blur', '[data-extra-fields] input', function() {
		var item = $(this).closest('[data-item]')
		var jsonVars = item.find('[name$=vars]')
		var extraFields = $(this).closest('[data-extra-fields] input')
		values = _.reduce(extraFields, function(a, b) { a[$(b).data('slug')] = $(b).val(); return a; }, {});
		jsonVars.val(JSON.stringify(values));
	});
	// Sortable related content buckets
	$('[data-sortable]').sortable({
		cancel: 'a,:input,label',
		cursor: 'move',
		// containment: 'parent',
		items: '> li',
		placeholder: 'placeholder',
		tolerance: 'pointer',
		start : function(event, ui) {
			$(event.target).find('.placeholder').height($(event.target).find('li').height())
		},
		update : function(event, ui) {
			// Re-sort items on update
			$(event.target).children().each(function(i, element) {
				$(element).find('[name$=sort]').val(i)
			});
		}
	});
	// Sortable container must be a whole number - no decimals
	$(window).on('resize', function() {
		$('[data-sortable].ui-sortable').each(function() {
			var sortable = $(this);
			sortable.css({'width': ''});
			sortable.css({'width': Math.floor(sortable.outerWidth())});
		});
	});
	// Prevents sortable container width set to 0 on open
	$('[data-slide-toggle]').on('click', function() {
		$('[data-sortable].ui-sortable').css({'width': ''});
		setTimeout(function() {
			// Set sortable container width
			$(window).trigger('resize');
		}, 500);
	});

	// Set up item browser for adding items
	itemBrowser = _.defaults({
		// Insert itemBrowser results into related item group
		'afterSubmit': function(e, results, widget) {
			var totalForms = $('.related.items [name$=TOTAL_FORMS]'),
				index = totalForms.val();
			$.each(results, function(i, result) {
				// Add index, sort and group values to result
				result['index'] = result['sort'] = index
				result['group'] = widget.target.data('group')
				widget.target.find('.empty-form').before(_.template($('[data-template=lineitem]').text(), result))
				index++
			})
			totalForms.val(index)
			renderExtraFields()
			$('[data-sortable]').sortable('refresh');
		}
	}, ModelBrowser);
	// Show extra fields on load
	renderExtraFields();
});

// Add extra fields to each related item dynamically
function renderExtraFields() {
	// Iterate related item groups
	$('[data-group]').each(function() {
		var extraFields = $(this).data('vars-fields'),
			extraTemplate = _.template($('[data-template=extra-fields]').text());
		// Iterate related items themselves
		$(this).find('[data-item]').each(function() {
			var self = $(this),
				values = $.parseJSON($(this).find('[name$="-vars"]').val() || '{}')
			// Don't add if this item already has extra fields
			if ($(this).find('[data-extra-fields]').length) return
			$.each(extraFields, function(index, field) {
				field['value'] = values[field['slug']]
				self.append(extraTemplate(field));
			})
		})
	})
}
