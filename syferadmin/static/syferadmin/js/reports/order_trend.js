OrderTrendReport = {
	token: "order_trend",
	graph: function(data) {
		var chart = nv.models.linePlusBarChart()
			.x(function(d,i) { return i })
			.y(function(d) { return d[1] })
			.color(d3.scale.category20().range())

		// Change x axis depending on interval
		var formatString
		if (data[0].values[1][0] - data[0].values[0][0] < 24 * 3600 * 1000) formatString = '%a %-I%p'
		else formatString = '%x'

		chart.xAxis
			.tickFormat(function(d) {
				var dx = data[0].values[d] && data[0].values[d][0] || 0;
				if (!dx) return null
				return d3.time.format(formatString)(new Date(dx))
			});

		chart.y1Axis.tickFormat(function(d) { return '$' + d3.format(',f')(d) });

		chart.y2Axis.tickFormat(d3.format(',f'));

		chart.bars.forceY([0])
		chart.lines.forceY([0])

		d3.select(this.container.get(0)).select('svg')
			.datum(data)
			.transition().duration(1000)
			.call(chart)

		nv.utils.windowResize(chart.update);

		return chart;
	},
	render: function(data) {
		Report.render.call(this, data)
		nv.addGraph($.proxy(this.graph, this, data));
	}
}

Dashboard.add(OrderTrendReport)