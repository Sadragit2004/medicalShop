from django.shortcuts import render
import web.settings as sett
# Create your views here.




def media_admin(request):

    context = {
        'media_url':sett.MEDIA_URL
    }

    return context



def main(request):

    return render(request,'main_app/main.html')

