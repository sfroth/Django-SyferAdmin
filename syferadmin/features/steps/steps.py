from . import utils

#
# Actions
#

@when(u'I log out')
def impl(context):
	br = context.browser
	br.find_by_css('.user-options').click()
	br.is_text_present('Log Out', 10)
	br.find_link_by_text('Log Out').click()

#
# Assertions
#

@then(u'I see the home page')
def impl(context):
	return the_url_is(context, '/')

@then(u'I see the login page')
def impl(context):
	assert context.browser.is_text_present('sign in')
