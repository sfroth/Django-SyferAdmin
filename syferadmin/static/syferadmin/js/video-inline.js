/*
Note to future developers: Please refactor this file before adding any new functionality to it.
*/
$(function() {

	var $video_container = $('.videos'),
		$video_ul = $video_container.find('ul'),
		prefix = $video_container.data('prefix');

	$video_ul.sortable({
		cancel: 'a,:input,label',
		cursor: 'move',
		containment: 'parent',
		distance: 5,
		forcePlaceholderSize: true,
		items: '> li',
		placeholder: 'placeholder',
		tolerance: 'pointer',
		start : function(event, ui) {
			$(event.target).find('.placeholder').height($(event.target).find('li').height()).width($(event.target).find('li').width());
		},
		update : function(event, ui) {
			resetSorts();
		}
	});

	function resetSorts() {
		$video_ul.find('li').not('.empty-form').each(function(index, item) {
			$(this).find('input[id$="sort"]').val(index);
		});
	}

	$('body').on('click submit', '.new-video', function(e) {
		e.preventDefault();
		e.stopPropagation();

		var $this = $(this),
			$container = $this.closest('.videos'),
			$input = $container.find('.video-search'),
			max = parseInt($this.data('max'), 10),
			template = $('.videos .empty-form'),
			form_id = $container.attr('id'),
			$TOTAL_FORMS = $container.find(':input[name$="TOTAL_FORMS"]'),
			$INITIAL_FORMS = $container.find(':input[name$="INITIAL_FORMS"]'),
			videoList = $container.find('ul');

		$.post($this.data('url'), {videos: $input.val()}, function(data) {
			if (!data.videos.length) {
				window.alert('I couldn\'t find a Youtube or Vimeo ID in that. Can you try again?');
				return
			}

			$.each(data.videos, function(index, values) {
				var video = template.clone();
				var index = $container.find('.inline-related:not(.empty-form)').length

				$.each(values, function(key, value) {
					if (key == 'thumb') video.find('img').attr('src', value);
					video.find(':input[name$="' + key + '"]').val(value);
				});

				video.find(':input').each(function(i, item) {
					var id_regex = new RegExp("(" + prefix + "-(\\d+|__prefix__))"),
						replacement = prefix + "-" + index;

					$(this).attr('id', $(this).attr('id').replace(id_regex, replacement));
					$(this).attr('name', $(this).attr('name').replace(id_regex, replacement));
				});

				videoList.prepend(video.removeClass('empty-form'));
				$TOTAL_FORMS.val(parseInt($TOTAL_FORMS.val(), 10) + 1);
			});

			resetSorts();

			$input.val('');
		});

	}).on('click', '.videos .delete', function(e) {

		var $this = $(this),
			video = $this.closest('li'),
			$DELETE = video.find('[name$="DELETE"]');

		if(!confirm('Are you sure you want to remove this video?')) {
			return false;
		}

		if ($DELETE.length > 0) {
			video.fadeOut();
			$DELETE.attr('checked', true);
		} else {
			video.fadeOut(function(e) { $(this).remove(); });
		}

	}).on('keypress', '.videos .video-search', function(e) {

		if(e.which == 13) {
			e.stopPropagation();
			e.preventDefault();
			$('.new-video').trigger('click');
		}

	});

});