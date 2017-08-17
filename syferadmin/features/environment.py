from splinter.browser import Browser

def before_scenario(context, scenario):
	context.browser = Browser()

def after_scenario(context, scenario):
	context.browser.quit()
	context.browser = None