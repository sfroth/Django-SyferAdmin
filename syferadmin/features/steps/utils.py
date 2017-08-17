# Some generic steps that can be reused across apps
import time
from behave import when, then, given, step_matcher
from django.core.urlresolvers import reverse
import factory
import random
from urlparse import urljoin


class UserFactory(factory.django.DjangoModelFactory):
	FACTORY_FOR = 'syferadmin.User'
	password = factory.PostGenerationMethodCall('set_password', 'user_test')

#################################
# Regex steps 					#
# ###############################
step_matcher('re')

#
#
# GIVEN
#
#


@given(r'I am on the (?P<page>[-\:\w]+)(?: page)?')
def impl(context, page):
	visit(context, reverse(page))

#
#
# WHEN
#
#


@when(r'I (?:click(?: on)?|follow) "(?P<text>.+)" for "(?P<parent>.+)"')
def click_in(context, text, parent):
	element = context.browser
	element = element.find_by_xpath("//li[contains(.,'" + parent + "')]|//tr[contains(.,'" + parent + "')]")
	link = element.first.find_by_xpath(".//a[contains(.,'" + text + "')]")
	link.click()


@when(r'I (?:click(?: on)?|follow) "(?P<text>.+)"')
def click(context, text):
	element = context.browser
	link = element.find_link_by_partial_text(text)
	if link:
		link.click()
		return
	other_elements = element.find_by_value(text).click()
	if other_elements:
		other_elements.click()


@when(r'I find "(?P<css>.+)" and (?:click(?: on)?|follow)(?: it)?')
def click_css(context, css):
	browser = context.browser
	browser.find_by_css(css).first.click()


@when(r'I hover(?: on)? "(?P<text>.+)"')
def hover(context, text):
	element = context.browser.find_by_xpath(".//strong[contains(.,'" + text + "')]")
	element.mouse_over()


@when(r'I have (?:a |the )?cookie "(?P<cookie>.+)" with the value of "(?P<value>.+)"')
def add_cookie(context, cookie, value):
	context.browser.cookies.add({'visited': 'true'})


@when(r'I pause for "(?P<seconds>.+)"(?: second(?:s)?)?')
def pause(context, seconds):
	time.sleep(float(seconds))

#
#
# THEN
#
#


@then(r'I should (?:see|be on) the (?P<page>\w+)(?: page)?')
def impl(context, page):
	assert page.lower() in context.browser.find_by_tag('h2').first.text.lower()


#################################
# Parse steps 					#
# ###############################
step_matcher('parse')

#
#
# Prerequisites
#
#


@given(u'a {type} user')
def create_user(context, user_type):
	context.email = 'test{}@fakeemailaddressdomain.com'.format(str(random.randint(0, 20000)))
	kwargs = {'email': context.email, 'is_active': True}
	if user_type == 'staff':
		kwargs.update({'is_staff': True, 'is_superuser': True})
	elif user_type == 'fake':
		kwargs['is_active'] = False
	UserFactory.create(**kwargs)


@given(u'I am logged in as an admin')
def impl(context):
	if context.browser.is_element_present_by_id('user-tools'):
		return True
	create_user(context, 'staff')
	log_in(context)

#
#
# Actions
#
#


@when(u'I check "{field}"')
def check(context, field):
	br = context.browser
	br.check(field)


@when(u'I fill in "{field}" with "{value}"')
def fill_in(context, field, value):
	br = context.browser
	br.fill(field, value)


@when(u'I log in')
def log_in(context):
	br = context.browser
	visit(context, '/admin/')
	br.fill('username', context.email)
	br.fill('password', 'user_test')
	br.find_by_css('[type=submit]').click()


@when(u'I select "{value}" for "{field}"')
def select(context, field, value):
	br = context.browser
	br.select(field, value)


@when(u'I uncheck "{field}"')
def uncheck(context, field):
	br = context.browser
	br.uncheck(field)


@when(u'the user visits "{url}"')
def visit(context, url):
	full_url = urljoin(context.config.server_url, url)
	context.browser.visit(full_url)


#
#
# Assertions
#
#


@then(u'"{text}" should be selected')
def impl(context, text):
	for element in context.browser.find_by_css('.active'):
		if element.text == text:
			return True
	return False


@then(u'I see an error message')
def impl(context):
	assert context.browser.is_element_present_by_css('.error')


@then(u'I should not see "{text}" in "{selector}"')
def impl(context, text, selector):
	assert text not in context.browser.find_by_css(selector).text


@then(u'I should see "{text}"')
def impl(context, text):
	assert context.browser.is_text_present(text)


@then(u'the url is "{url}"')
def the_url_is(context, url):
	path_info = context.browser.url.replace(context.config.server_url, '')
	assert path_info == url
