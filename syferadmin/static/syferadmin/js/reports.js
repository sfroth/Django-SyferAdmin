$(function () {
	/**
	 * Load existing dashboard state and initialize
	 * The current dashboard string is a global to store the current report page
	 */
	removeSpaces = new RegExp('[ ]', 'g');
	if (!('currentDashboard' in window))
		currentDashboard = 'dashboard'
	currentDashboard = currentDashboard.replace(removeSpaces, '');
	Dashboard.init(currentDashboard);
	// Force refresh if we're on the dashboard. Otherwise delay a few seconds to mess with the report
	Dashboard.refresh($('body').is('.dashboard'));
});

// Report object
var Report = {
	token: null,
	detail: false,
	init: function(dashboard) {
		this.container = $("[data-report=" + this.token + "]")
		this.body = this.container.find('[data-body]')
		this.dashboard = dashboard
		this.template = _.template(this.container.find('[data-template]').text())
		this.url = '/admin/reports/' + this.token + '/'
		this.export_url = '/admin/reports/export/' + this.token + '/'
		this.pool_url = '/admin/reports/poll/'
		this.enabled = true
		this.bindUI()
	},
	// Bind UI elements
	bindUI: function() {
		this.container.find('[data-action=toggle]').on('click', $.proxy(this.toggle, this))
	},
	setLoading: function() {
		if (this.container) {
			this.container.addClass('loading');
		}
	},
	fetch: function(force) {
		var self = this;
		// Skip if closed/disabled
		if (!this.enabled) return false;

		// Set parameters
		params = {
			start_date: this.dashboard.startDate.format('yyyy-mm-dd'),
			end_date: this.dashboard.endDate.format('yyyy-mm-dd'),
			range: this.dashboard.range,
			force: force,
			detail: this.detail ? "1" : "0",
		}
		// this.parameters are set with inline js on syferadmin/templates/reports/detail.html
		var this_report_params = this.hasOwnProperty('parameters') ? this.parameters : (typeof report_params !== 'undefined' ? report_params : null)
		if (this_report_params) {
			$.each(this_report_params, function(key, val) {
				params[key] = val;
			});
		}

		// Load content
		$('#report-block-overlay').show()
		this.body.html('');
		var report = this
		$.ajax(this.url, {data: params}).success(function(data){
			if(data && data.job_id){
				self.pool_data(data.job_id);
			} else {
				self.render(data);
			}
		}).error(function(data) {
			report.container.removeClass('loading').addClass('error');
			$('#report-block-overlay').hide()
			report.body.html('<h2>Error Loading Data</h2>');
		});
		if (report.container.find('.region_map').length > 0) {
			params.detail = '0';
			// $.ajax(this.url, {data: params}).success($.proxy(this.render_map, this)).error(function(data) {
			// 	report.container.find('.region_map').hide();
			// });
			$.ajax(this.url, {data: params}).success(function(data){
				if(data && data.job_id) {
					self.pool_data(data.job_id, 'render_map');
				} else {
					self.render_map(data);
				}
			}).error(function(data) {
				report.container.find('.region_map').hide();
			});
		}
	},
	pool_data: function(job_id, callback){
		var self = this,
			callback = typeof callback === "undefined" ? 'render' : callback;
		function handle_error(xhr, textStatus, errorThrown) {
			clearInterval(interval_id);
			alert("Please report this error: "+errorThrown+xhr.status+xhr.responseText);
		}

		function show_status(data) {
			number_of_checks++;
			if (data.error) {
				clearInterval(interval_id);
				self[callback](data);
			} else if (data.status == "solved") {
				clearInterval(interval_id);
				self[callback](data.result);
			} else if (data.status == "error") {
				clearInterval(interval_id);
				self[callback](data);
			} else if (self.detail && number_of_checks > 61) {
				//for detail reports, if report takes more than 60 seconds (61 calls to this method) to execute, alert the user that they will receive the response via email
				clearInterval(interval_id);
				self[callback]({'error': 'This report is taking a long time to run. The result will be emailed to you.'});
			}
		}

		function check_status() {
			$.ajax({
				type: "POST",
				url: self.pool_url,
				data: {'task_id': job_id},
				success: show_status,
				error: handle_error
			});
		}

		var number_of_checks = 0
		setTimeout(check_status, 0.05);
		// Check every second
		var interval_id = setInterval(check_status, 1000);
	},
	record_count: function(count) {
		var rc = $('.record-count');
		rc.text('').hide();
		if(rc.length > 0) {
			rc.text(count).show();
		}
	},
	render: function(data) {
		this.container.removeClass('loading error').addClass('loaded');
		$('#report-block-overlay').hide()
		if (!$.isEmptyObject(data)) {
			if (data.error) {
				this.body.html('<h2>'+data.error+'</h2>');
			} else {
				if (this.detail && $('th.sorted').length > 0) {
					// Sort data
					data.results.sort(function(a,b) {
						var sortOrder = $('th.sorted').hasClass('ascending') ? 1 : -1;
						var property = $('th.sorted').data('field');
						return sortOrder * ((a[property] < b[property]) ? -1 : (a[property] > b[property]) ? 1 : 0);
					});
				}
				this.body.html(this.template(data));
			}
			this.record_count(_.size(data.results));
			this.body.html(this.template(data));
		} else {
			this.body.html('<h2>No data found</h2>');
		}
	},
	render_map: function(data) {
		var report = this
		var region = report.hasOwnProperty('parameters') && 'rgn' in report.parameters && report.parameters['rgn'] ? report.parameters['rgn'] : null;

		function drawMap() {
			var data_array = data[0].values.slice(0)
			data_array.unshift(['Location', data[0].key]);
			var map_data = google.visualization.arrayToDataTable(data_array);

			report.container.find('.region_map').show();
			var container = report.container.find('.region_map')[0];
			var geomap = new google.visualization.GeoChart(container);

			var options = {};
			options['dataMode'] = 'regions';
			if (region) {
				options['region'] = region;
				options['resolution'] = 'provinces';
			} else {
				google.visualization.events.addListener(geomap, 'regionClick', function(eventData) {
					if (location.search) {
						window.location.href = [location.protocol, '//', location.host, location.pathname, location.search, '&rgn=', eventData.region].join('');
					} else {
						window.location.href = [location.protocol, '//', location.host, location.pathname, '?rgn=', eventData.region].join('');
					}
				});
			}
			if (report.hasOwnProperty('parameters') && 'map_number_currency' in report.parameters && report.parameters['map_number_currency']) {
				var formatter1 = new google.visualization.NumberFormat({fractionDigits:2, prefix:'$'});
				formatter1.format(map_data, 1);
				options['legend'] = {numberFormat:'$###,###.##'}
			}

			geomap.draw(map_data, options);
		}
		google.load("visualization", "1", {packages:["geochart"], callback: drawMap});
	},
	do_export: function(format) {
		var report = this
		params = {
			start_date: this.dashboard.startDate.format('yyyy-mm-dd'),
			end_date: this.dashboard.endDate.format('yyyy-mm-dd'),
			range: this.dashboard.range,
		}
		if (this.hasOwnProperty('parameters')) {
			// this.parameters are set with inline js on syferadmin/templates/reports/detail.html
			$.each(this.parameters, function(key, val) {
				params[key] = val;
			});
		}
		this.setLoading();
		$('#report-block-overlay').show()
		$.ajax(this.export_url + format + '/', {data: params}).success(function(data){
			report.container.removeClass('loading')
			$('#report-block-overlay').hide()
			if(data && data.job_id){
				report.pool_data(data.job_id, 'perform_export');
			} else {
				report.perform_export(data);
			}
		}).error(function(data) {
			report.container.removeClass('loading')
			$('#report-block-overlay').hide()
			alert('Error exporting report')
		});
	},
	perform_export: function(data) {
		if (data.error) {
			this.body.html('<h2>'+data.error+'</h2>');
		} else {
			window.location.href = data.file_url;
		}
	},
	toggle: function() {
		this.enabled = !this.enabled
		if (this.enabled) {
			this.body.slideDown()
		}
		else {
			this.body.slideUp()
		}
		this.container.toggleClass('open', this.enabled).toggleClass('closed', !this.enabled)
	}
}

// Dashboard object
var Dashboard = {
	reports: [],
	range: 'day',
	force: false,
	fetchTimeoutHandle: 0,
	init: function(page) {
		this.pageName = page;
		this.bindUI()

		var settings = this.getSettingsCookie();

		if ($('[name=force_start_date][type=hidden]').length > 0) {
			this.force = true;
			this.startDate = this.parseDate($('[name=force_start_date][type=hidden]').val())
			this.endDate = this.parseDate($('[name=force_end_date][type=hidden]').val(), '23:59:59')
		} else if (settings) {
			// Load settings from cookie
			_.extend(this, settings)

			this.startDate = new Date(this.startDate)
			this.endDate = new Date(this.endDate)
			// Filtering by type=date so the start_date in schedulable forms
			// don't get modified as well because they are datetime fields
			$('[name=start_date][type=date]').val(this.startDate.format("yyyy-mm-dd"))
			$('[name=end_date][type=date]').val(this.endDate.format("yyyy-mm-dd"))
		}
		this.setRange()

		_.invoke(this.reports, 'init', this)
	},
	// Dashboard settings cookie
	getSettingsCookie: function() {
		var cookie = $.cookie(this.pageName + '.settings')
		if ($.isEmptyObject(cookie)) {
			return null
		} else {
			return cookie
		}
	},
	// Save dashboard settings to cookie
	save: function() {
		$.cookie(this.pageName + '.settings', {'range': this.range, 'startDate': this.startDate, 'endDate': this.endDate}, {expires: 90})
	},
	// Add report
	add: function(report) {
		report = _.extend(Object.create(Report), report)
		this.reports.push(report)
	},
	// Bind UI elements
	bindUI: function() {
		var self = this;
		// Trigger refresh
		$('[data-action=refresh]').on('click', $.proxy(this.refresh, this));
		// Set range
		$('[data-ranges]').on('click', 'button', function() {
			if ($(this).data('range') == 'custom') {
				self.open();
			}
			else {
				self.setRange($(this).data('range'))
			}
		});
		$('body').on('click', '[data-ui="custom"],[data-range="custom"]', function(e){
			e.stopPropagation();
		}).on('click', function(e){
			// Don't close the UI if it is just changes to the datepicker
			if($(e.target).is('[class*=ui-datepicker]') || $(e.target).closest('[class*=ui-datepicker]').length > 0) {
				return;
			}
			self.close();
		});
		$(document).on('keyup', function(e){
			if(e.which == 27) self.close();
		});
		// Update custom range on change
		$('#custom').on('click', $.proxy(this.setRange, this, 'custom'))
		// Export to csv (detail page only)
		$('.export').on('click', function() {
			_.invoke(self.reports, 'do_export', $(this).data('format'))
		});
		$('.sortable a').on('click', function() {
			var $th = $(this).closest('.sortable');
			$th.siblings().removeClass('sorted ascending descending');
			if ($th.hasClass('sorted') && $th.hasClass('descending')) {
				$th.removeClass('sorted descending');
			} else if ($th.hasClass('sorted')) {
				$th.removeClass('ascending').addClass('descending');
			} else {
				$th.addClass('sorted ascending');
			}
			self.refresh();
		});
	},
	close: function() {
		var overlay = $('[data-ui=custom]');
		if(overlay.is('.open')) overlay.removeClass('open').slideUp();
	},
	open: function() {
		var overlay = $('[data-ui=custom]');
		if(!overlay.is('.open')) overlay.addClass('open').slideDown();
	},
	parseDate: function(datestr, time) {
		var date = $.datepicker.parseDate('yy-mm-dd', datestr),
			local_tz = date.toString().match(/([-\+][0-9]+)\s/)[1];

		if(!time) {
			time = '00:00:00';
		}
		local_tz = local_tz.substr(0, local_tz.length - 2) + ':' + local_tz.substr(-2);
		return new Date($.datepicker.formatDate('yy-mm-dd', date) + 'T' + time + local_tz);
	},
	// Refresh entire dashboard
	refresh: function(force) {
		//put this on hold for 10 seconds to make sure the user isn't making a lot of changes
		//and make sure to only exec once
		if (this.fetchTimeoutHandle) {
			clearTimeout(this.fetchTimeoutHandle);
		}

		_.invoke(this.reports, 'setLoading');

		if (force) {
			_.invoke(this.reports, 'fetch')
		} else {
			this.fetchTimeoutHandle = setTimeout("Dashboard.refresh(true)", 5000);
		}
	},
	// Set start/end dates based on selected range
	setRange: function(range) {
		if (range) {
			this.range = range
		}
		// For custom ranges, don't create start/end dates
		if (this.range == 'custom') {
			// Only grab ones that are type=date
			this.startDate = this.parseDate($('[name=start_date][type=date]').val());
			this.endDate = this.parseDate($('[name=end_date][type=date]').val(), '23:59:59');
		}
		// Create start/end dates based on selected range
		else {
			if(!this.force || !this.startDate) {
				// Set end date to now
				this.endDate = new Date();

				// Set start date based on end date and range
				this.startDate = new Date(this.endDate);
				switch(this.range) {
					case 'month':
						this.startDate = new Date(this.endDate.getFullYear(), this.endDate.getMonth(), 1);
						break;
					case 'week':
						this.startDate.setDate(this.endDate.getDate() - 6);
						break;
					case 'year':
						this.startDate = new Date(this.endDate.getFullYear(), 0, 1);
						break;
				}

				// Only grab ones that are type=date
				$('[name=start_date][type=date]').val(this.startDate.format("yyyy-mm-dd"));
				$('[name=end_date][type=date]').val(this.endDate.format("yyyy-mm-dd"));
			}
		}

		// check for backwards dates
		if(this.startDate > this.endDate) {
			alert('Start date can not be after the end date. Please try again.');
			return;
		}

		$('[name=start_date][type=date]').val(this.startDate.format("yyyy-mm-dd"));
		$('[name=end_date][type=date]').val(this.endDate.format("yyyy-mm-dd"));

		// Update the date range under page title
		var tz = $('header[data-tz-abbrev]').data('tz-abbrev');
		tz = tz ? ' ' + tz : '';
		if (this.range == 'day') {
			$('[data-start-date]').text('12:00AM' + tz);
			$('[data-end-date]').text('Now');
		} else {
			$('[data-start-date]').text(this.startDate.format("mm/dd/yyyy") + tz);
			$('[data-end-date]').text(this.endDate.format("mm/dd/yyyy") + tz);
		}
		// Make sure start dates are 00:00 and end dates are 23:59
		this.startDate.setHours(0, 0, 0);
		this.endDate.setHours(23, 59, 0);
		// Set active state
		$('[data-range=' + this.range + ']').closest('li').addClass('active').siblings().removeClass('active');
		// Hide time range if this report doesn't use it
		if($('[data-range]').length === 0) {
			$('.dashboard-date-range').hide();
		}
		// Save settings
		this.save();
		this.refresh();
		this.close();
		return false;
	}
}

// Allow JSON storage in cookies
$.cookie.json = true;

function numberWithCommas(x) {
	return x.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}
