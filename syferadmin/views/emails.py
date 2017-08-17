from django.contrib.auth.decorators import permission_required
from django.http import HttpResponse
from django.template.response import TemplateResponse

from syferadmin import emails


@permission_required('emails.can_test')
def email_test(request, email_type=None, param=None):
	"Test an email, either viewing it directly or sending it out"
	if not email_type:
		return TemplateResponse(request, 'syferadmin/emails.html', {'emails': emails})

	email_obj = emails.get(email_type)
	mail = email_obj.get_email(request=request, param=param)

	if 'to' in request.GET:
		mail.to = [request.GET['to']]
		mail.send()

	default = 'text'
	content_types = {'text': u'<pre style="white-space: pre-wrap;">{}</pre>'.format(mail.body)}
	# Only show html type if it exists
	if hasattr(mail, 'alternatives'):
		default = request.GET.get('type', 'html')
		content_types['html'] = mail.alternatives[0][0]

	return HttpResponse(content_types[default])
