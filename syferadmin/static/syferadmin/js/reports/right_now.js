RightNowReport = {
	token: "right_now",
	render: function(data) {
		Report.render.call(this, data)
		active_users = this.body.find('.total span')
		animate = new countUp(active_users.get(0), 0, parseInt(active_users.text()))
		animate.start()
	}
}

Dashboard.add(RightNowReport)