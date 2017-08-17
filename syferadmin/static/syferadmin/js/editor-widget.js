/**
 * Action for drawing an image and showing the library
 */
function drawImageAndShowLibrary(editor) {

	library = $('.library');
	library.slideToggle();

	// Set active state
	var toolbar_icon = $(editor.toolbar.image);
	toolbar_icon.toggleClass('active');

}
/**
 * Action for drawing a video
 */
function drawVideo(editor) {
	var cm = editor.codemirror;
	var pos = cm.getCursor('start');
	video_url = prompt("Enter the Youtube or Vimeo URL:\n\n\E.G. http://youtube.com/watch?v=8X_Ot0k4XJc")
	if (!video_url) return false;
	cm.replaceRange('![Video](' + video_url + ')', pos);
}

$(document).ready(function () {

	var toolbar = [
		{name: 'bold', action: Editor.toggleBold, title: 'Make text bold'},
		{name: 'italic', action: Editor.toggleItalic, title: 'Make text italic'},
		'|',

		{name: 'quote', action: Editor.toggleBlockquote, title: 'Insert blockquote'},
		{name: 'unordered-list', action: Editor.toggleUnOrderedList, title: 'Insert list'},
		{name: 'ordered-list', action: Editor.toggleOrderedList, title: 'Insert numbered list'},
		'|',

		{name: 'link', action: Editor.drawLink, title: 'Insert link'},
		{name: 'image', action: drawImageAndShowLibrary, title: 'Insert image'},
		{name: 'video', action: drawVideo, title: 'Insert YouTube/Vimeo video'},
		'|',

		{name: 'info', action: 'http://lab.lepture.com/editor/markdown', title: 'Help'},
		{name: 'preview', action: Editor.togglePreview, title: 'Preview'},
		{name: 'fullscreen', action: Editor.toggleFullScreen, title: 'Edit fullscreen'}
	]

	$('.editor').each(function() {

		widget = $(this);
		var editor = new Editor({'toolbar': toolbar});
		editor.render(widget.find('textarea').get(0));
		widget.data('editor', editor);

	});

});