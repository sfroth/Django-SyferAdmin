var poller;

$(function () {

	$('.add-row a').on('click', initUploaders);
	initUploaders();

});

function initUploaders() {

	$('.uploader').each(function() {

		var uploader = $(this);

		// Skip if already initialized
		if (uploader.data('initialized')) return true;

		// Grab options from data attribute set in Django
		var uploadList = uploader.find('ul');
		var dropArea = uploader.find('.drop-area');
		var options = uploader.data("options");
		var attach = options.reversed ? uploadList.prepend : uploadList.append;

		// Add CSRF token
		if (!options.request.customHeaders) options.request.customHeaders = {};
		options.request.customHeaders["X-CSRFToken"] = getCookie('csrftoken');
		if (!options.deleteFile.customHeaders) options.deleteFile.customHeaders = {};
		options.deleteFile.customHeaders["X-CSRFToken"] = getCookie('csrftoken');

		// Sortable
		uploader.find('> ul').each(function() {
			if ($(this).closest('.uploader').data('options').validation.itemLimit > 1) {
				var connectWith = false;
				if($(this).data('connectWith')) {
					connectWith = $(this).data('connectWith');
				}
				$(this).sortable({
					connectWith: connectWith,
					items : 'li',
					placeholder : 'placeholder',
					forcePlaceholderSize: true,
					receive: function(event, ui) {
						if(ui.item.find('[name$="-images_group"]').length > 0) {
							ui.item.find('[name$="-images_group"]').val(ui.item.closest('[data-image-group]').data('image-group'));
						}
					},
					start: function(event, ui) {
						ui.placeholder.height(ui.item.height());
						ui.item.parents().each(function(){
							if($(this).css('position') === 'relative') {
								$(this).addClass('temp-position-relative').css('position', 'static');
							}
						});
						ui.item.closest('.ui-sortable').sortable('refresh');
						if(ui.item.closest('[data-image-groups]:not([data-image-groups=""])').length > 0) {
							var list = ui.item.closest('[data-image-groups]:not([data-image-groups=""])').find('[data-image-group] .ui-sortable').addClass('temp-overflow-hidden');
							list.each(function(){
								$(this).css('overflow', 'hidden');
								$(this).css({
									height: $(this).outerHeight(),
									display: 'block',
									'min-height': '185px',
									overflow: 'visible'
								});
							});
							$('.upload-button').hide();
						}

					},
					stop: function(event, ui) {
						$('.temp-position-relative').css('position', 'relative');
						$('.temp-overflow-hidden').css({
							width: 'auto',
							height: 'auto',
							'min-height': '10px'
						});
						$('.upload-button').show();
					},
					update: function(event, ui){
						$(event.target).find('li').each(function(index, item){
							// $(this).find('input[id$="Sort"]').val(index);
						});
					}
				});
			}
		});

		options.button = uploader.find('.upload-button')[0];
		uploader.fineUploader(options)
		.on('error', function(e, id, name, reason) {

			alert('Error! ' + reason);
			$('body').trigger('dragfinish');
			event.stopPropagation();

		})
		// Adding item to upload queue
		.on('upload', function(e, id, name) {
			$('body').trigger('dragfinish');

			uploadItem = $('<li data-id="' + id + '"><span class="progress"></span><span class="delete cancel">Cancel</span></li>');
			attach.call(uploadList, uploadItem);
			uploadItem.closest('ui-sortable').sortable('refresh');
			uploadItem.addClass('loading');

			// Hide upload button if max files limit has been reached
			if (options.validation.itemLimit !== 0 && uploader.find('li').length >= options.validation.itemLimit) uploader.find(".upload-button").hide();

		})
		// Upload progress
		.on('progress', function(e, id, name, uploaded, total) {
			var progressamount = Math.round(uploaded / total * 100) + "%";
			uploadList.find('[data-id=' + id + '] .progress').width(progressamount).attr("data-progress", progressamount);
		})
		// Item cancelled
		.on('cancel', function(e, id, name) {
			uploader.removeItem(id);
			$('body').trigger('dragfinish');
		})
		// Item upload completed
		.on('complete', function(e, id, name, data) {

			if (!data.success) return false;
			$('body').trigger('dragfinish');
			uploadItem = uploadList.find('[data-id=' + id + ']').removeClass('loading');
			uploadItem.find('.progress').remove();
			uploadItem.find('.cancel').removeClass('cancel').text('Delete');
			uploadItem.data('uuid', data.uuid);
			// Add thumbnnail
			if(data.thumb){
				uploadItem.prepend('<img src="' + data.thumb + '" />');
			} else {
				uploadItem.prepend('<img src="/static/syferadmin/img/document.png" />');
			}

			// Save uuid to hidden input file
			uploadItem.append('<input type="hidden" name="' + uploader.data('name') + '" value="' + data.uuid + '" />');
			if(uploadItem.closest('[data-image-groups]:not([data-image-groups=""])').length > 0) {
				uploadItem.append('<input type="hidden" name="' + uploader.data('name') + '_group" value="' + uploadItem.closest('[data-image-group]').data('image-group') + '" />');
			}
			if (options.description) {
				uploadItem.append('<input type="text" name="' + uploader.data('name') + '_description" value="" />');
			}

			// Remove noinput variable
			uploader.find('.noinput').remove();

			// Callback
			uploader.trigger("afterUpload", [uploadItem, name, data]);

		})
		// Delete complete
		.on('deleteComplete', function(e, id) {
			uploader.removeItem(id);
		})
		// Delete button
		.on('click', '.delete', function(e) {
			if (!confirm("Delete this file?")) return false;
			item = $(this).closest("li");
			// Callback
			uploader.trigger("beforeDelete", [item]);
			if (item.data('id') == undefined) uploader.removeItem(item);
			else $(this).hasClass("cancel") ? uploader.fineUploader("cancel", item.data('id')) : uploader.fineUploader("deleteFile", item.data('id'));
		});

		// Drag and drop events
		dropArea.fineUploaderDnd({ classes: { dropActive: "hover" }, hideDropZonesBeforeEnter: true })
		.on('processingDroppedFiles', function(e) {
			$('.drop-area').hide().removeClass('active');
			$('body').trigger('dragfinish');
		})
		.on('processingDroppedFilesComplete', function(e, files) {
			if (options.validation.itemLimit > 0 && uploadList.children().length >= options.validation.itemLimit) return false;
			uploader.fineUploader('addFiles', files);
			$('body').trigger('dragfinish');
		});

		var drag_count = 0;
		$(document).on('dragenter dragleave', function(e){
			drag_count += e.type === 'dragenter' ? 1 : -1;
			drag_count = Math.max(drag_count, 0);

			// fineUpload cancels the enter event, so we account for that
			if($('.drop-area.hover').length > 0) {
				$('body').addClass('dragging');
				drag_count = 2;
			} else {
				if(drag_count === 1) {
					$('body').addClass('dragging');
				}
				if(drag_count === 0) {
					$('body').trigger('dragfinish');
				}
			}
		});
		$('body').on('dragfinish', function(){
			drag_count = 0;
			$('body').removeClass('dragging');
		});

		uploader.data('initialized', true);

		// Remove files from UI
		uploader.removeItem = function(e) {
			// If passed an ID, get the list item first
			if (typeof e === 'number') e = uploadList.find('[data-id=' + e + ']')
			e.remove();
			if (e.siblings().length < options.validation.itemLimit) uploader.find(".upload-button").show();
			if (uploadList.children().length == 0) uploader.append('<input class="noinput" type="hidden" name="' + uploader.data('name') + '" value="" />')
		}

		// Video encoding progress tracker
		uploader.on("afterUpload", function(e, item, name, data) {
			if (data['type'] == 'video') {
				item.addClass("encoding");
				item.append('<span class="message">Encoding video... Please stand-by.</span>');
				$(".save-group button").prop("disabled", true);
				if (!poller) poller = setInterval(function() { check_encoding_complete(item, name, data); }, 5000);
			}
		});

	});

}

function check_encoding_complete(item, name, data) {
	$.getJSON('/admin/uploader/check/' + data['uuid'] + '/', function(data) {
		if (!data['encoded']) return;
		item.find(".message").hide();
		item.removeClass("encoding");
		$(".save-group button").prop("disabled", false);
		clearInterval(poller);
	});
}