var ModelBrowser = {

	cssClass: 'data-browser',
	exclude: [],
	target: null,
	totalPages: 1,
	triggerElement: $(),
	visible: false,
	scrollBottomTrigger: 400,

	init: function(contentType) {
		this.page = 1;
		this.container = $('[data-browser]');
		this.contentType = contentType;
		this.itemTemplate = _.template($('[data-template=item]').text());
		this.searchField = this.container.find('input[type=search]');
		this.results = this.container.find('[data-results]');
		this.resultsContainer = this.container.find('[data-results-container]');
	},
	// Callback after data-browser is finished loading
	afterShow: function(e) {
		this.triggerElement.removeClass('loading');
		this.container.removeClass('loading');
	},
	// Callback for handling results
	afterSubmit: function(e, results, widget) {},
	// Callback before data-browser opens
	beforeShow: function(e) {
		this.triggerElement.addClass('loading');
		this.container.addClass('loading');
	},
	bindUI: function() {
		var self = this;

		// Cancel browser usage
		this.container.find('[data-action=cancel]').on('click.modelBrowser', $.proxy(this.close, this));

		// Close overlay with esc key
		$(document).keydown(function(e) {
			if (e.keyCode == 27) self.close();
		});

		// Endless scrolling
		this.resultsContainer.on('scroll.modelBrowser', function() {
			var scrollFromBottom = $(this)[0].scrollHeight - $(this).height() - $(this).scrollTop();

			// Don't get more results unless there's pages and the user is 400px from the bottom
			if (self.container.hasClass('loading') || self.page >= self.totalPages || scrollFromBottom > self.scrollBottomTrigger) {
				return;
			}
			self.page++;
			self.getResults();
		});

		// Start search on typing
		this.searchField.on('keyup.modelBrowser', function() {
			self.page = 1;
			delay($.proxy(self.getResults, self), 150);
		// Restart search
		}).on('search.modelBrowser', function() {
			$(this).trigger('keyup');
		})

		// Mark/unmark selected items
		this.container.on('click.modelBrowser', '[data-result]', function() {
			$(this).toggleClass('selected');
		});

		// Submit selected items back
		this.container.find('[data-action=add]').on('click.modelBrowser', $.proxy(this.submit, this))

		// Keyboard shortcut for add
		var isMac = !!navigator.platform.match(/^Mac/),
			metaLabel = isMac ? '⌘' : 'ctrl';
		$(window).on('keydown', function(e){
			// Capture +enter to save form fields
			if (e.which === 13) {
				var meta = isMac ? e.metaKey : e.ctrlKey;
				if (meta && self.container.find('[data-action="add"]').length > 0) {
					self.container.find('[data-action="add"]').first().trigger('click');
				}
			}
		});
		// Add titles to fields showing the shortcuts
		this.container.find('[data-action="add"]').attr('title', '(' + metaLabel + '+enter)');

		this.visible = true;
		this.afterShow();

	},
	// Close browser
	close: function() {
		this.visible = false;
		$.fancybox.close();
		$('html').removeClass('fancybox');
		this.container.off('.modelBrowser').find('*').off('.modelBrowser');
	},
	onLoad: function(data, requestTime) {

		// Don't service stale requests
		self = this;
		if (self.requestTime && self.requestTime != requestTime) {
			return;
		}

		// Empty ul for page 1
		if (this.page < 2) {
			// Only remove tiles that aren't currently selected
			this.results.find('li.tile').not('.selected').remove();
		}

		// No data found
		if (!data.success) {
			if (!this.visible) {
				alert("There's nothing left!");
			}
			// Set counts to 0
			this.container.find('[data-count], [data-total]').text(0);
			// this.container.removeClass('loading')
			this.afterShow();
			return;
		}

		// Append results
		$.each(data.results, function(i, item) {
			// Only add items that aren't already selected

			if(self.results.find('[data-item-id="' + item['content_type_id'] + '-' + item['id'] + '"]').length === 0) {
				self.results.append(self.itemTemplate(item));
			}
		});

		// Update counts
		this.totalPages = data.pages;
		var children = this.results.children().length;
		this.container.find('[data-count]').text(children);
		// Take into account selected items as well as the result count
		this.container.find('[data-total]').text(Math.max(data.total, children));

		// Show overlay
		if (!this.visible) {
			$.fancybox(this.container, _.extend(window.fancyboxOptions, {
				'afterShow': $.proxy(self.bindUI, self),
				'closeBtn': false,
				'wrapCSS': self.cssClass
			}));
		}
		else this.afterShow();
	},
	// Request new results
	getResults: function() {

		var self = this;
		var searchValue = this.searchField.val();
		var searchCounter = this.container.find('.search-counter');
		var requestTime = new Date().getTime();
		self.requestTime = requestTime;
		this.beforeShow();

		$.get(
			'/admin/related_lookup/',
			{
				'content_type_id': this.contentType,
				'exclude': this.exclude.join(','),
				'page': this.page,
				'search': searchValue
			},
			// Function wrapper so we can keep track of the request time
			function(data) {
				self.onLoad(data, requestTime)
			},
			'json'
		);

	},
	// Open model browser
	open: function() {
		this.results.empty();
		this.searchField.val('');
		this.getResults();
	},
	// Submit selected files for processing
	submit: function(e) {
		// Gather selected items
		var results = [];
		this.results.find('.selected').each(function() {
			results.push($(this).data('object'));
		});
		if (!results.length) {
			alert("You didn't select any items!");
			return;
		}
		this.afterSubmit(e, results, this);
		this.close();
	}
}
