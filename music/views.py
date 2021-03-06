# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import copy

from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, permission_required


from music.models import Album, Song
from music.forms import AlbumForm, SongForm
from django.db.models import Q

from django.http import FileResponse
from django.utils.text import slugify
from django.views import View
from accounts.models import User

AUDIO_FILE_TYPES = ['wav', 'mp3', 'ogg']
IMAGE_FILE_TYPES = ['png', 'jpg', 'jpeg']

# from uploads.core.models import Document
# from uploads.core.forms import DocumentForm

# Create your views here.


def user_tracker(request, user_id):
    profile = get_object_or_404(User, id=user_id)
    try:
        user = User.objects.get(pk=user_id)
    except:
        raise ValueError('Not found')

    # Flag that determines if we should show editable elements in template
    editable = False
    # Handling non authenticated user for obvious reasons
    if request.user.is_authenticated() and request.user == user:
        editable = True

    owned = set(Album.objects.filter(users=request.user).values_list('users', flat=True))  
    
    data = {
        'editable': editable,
        'profile': profile,
        'owned' : owned
    }
    return data


def filters(user_id, filter_by):
    q_genre = set(Album.objects.filter(users=user_id).values_list('genre', flat=True))
    q_artist = set(Album.objects.filter(users=user_id).values_list('artist', flat=True))
    
    if filter_by in q_genre:
        albums = Album.objects.filter(users=user_id, genre=filter_by)
    elif filter_by in q_artist:
        albums = Album.objects.filter(users=user_id, artist=filter_by)
    else:
        albums = Album.objects.filter(users=user_id)

    data = {
        'albums': albums,
        'q_genre': q_genre,
        'q_artist': q_artist,
    }
          
    return data


def library_view(request, user_id, filter_by = None):
    q_genre = set(Album.objects.filter(users=user_id).values_list('genre', flat=True))
    q_artist = set(Album.objects.filter(users=user_id).values_list('artist', flat=True))
    songs = None
    context_user = user_tracker(request, user_id)

    if filter_by:
        context_data = filters(user_id, filter_by)
    else:
        albums = Album.objects.filter(users=user_id)
        context_data = {
            'albums': albums,
            'q_genre': q_genre,
            'q_artist': q_artist
        }
    
    query = request.GET.get("search")
    if query:
        print('+++++++++',query)

        albums = albums.filter(
            Q(album_title__icontains=query) |
            Q(artist__icontains=query)
        ).distinct()
        songs = Song.objects.all()
        songs = songs.filter(album__users=user_id)
        songs = songs.filter(
            Q(song_title__icontains=query)
            ).distinct()
        context_data = {
            'albums': albums,
            'q_genre': q_genre,
            'q_artist': q_artist,
            'songs': songs
            }
        context = {**context_user, **context_data}
        return render(request, "music/my_library.html", context, {'filter_by': filter_by})
    else:
        context = {**context_user, **context_data}
        return render(request, "music/my_library.html", context, {'filter_by': filter_by})

# def filters(request, user_id, filterby):
#     profile = get_object_or_404(User, id=user_id)
#     albums = Album.objects.filter(user=user_id)
#     q_genre = set(Album.objects.filter(user=user_id).values_list('genre', flat=True))
#     q_artist = set(Album.objects.filter(user=user_id).values_list('artist', flat=True))

#     if filterby in q_genre:
#         albums = Album.objects.filter(user=user_id, genre=filterby)
#     else:
#         albums = Album.objects.filter(user=user_id, artist=filterby)

#     try:
#         user = User.objects.get(pk=user_id)
#     except:
#         raise ValueError('Not found')

#     # Flag that determines if we should show editable elements in template
#     editable = False
#     # Handling non authenticated user for obvious reasons
#     if request.user.is_authenticated() and request.user == user:
#         editable = True

#     context = {
#         'albums'    :albums,
#         'q_genre'   :q_genre,
#         'q_artist'  :q_artist,
#         'filter_by' :filterby,
#         'editable' : editable,
#         'pro'      : profile
        

#     }
#     return render(request, 'music/my_library.html', context)




@login_required
def upload_album_view(request):
    if not request.user.is_authenticated():
        return render(request, 'login.html')
    else:
        form = AlbumForm(request.POST or None, request.FILES or None)
        if form.is_valid():
            album = form.save()
            user = User.objects.get(pk=request.user.id)
            album.users.add(user)
            album.album_logo = request.FILES['album_logo']
            file_type = album.album_logo.url.split('.')[-1]
            file_type = file_type.lower()
            if file_type not in IMAGE_FILE_TYPES:
                context = {
                    'album': album,
                    'form': form,
                    'error_message': 'Image file must be PNG, JPG, or JPEG',
                }
                return render(request, 'music/upload_album.html', context)
            album.save()
            return render(request, 'music/album_detail.html', {'album': album})
            # return redirect('pages/profile_home.html')
        context = {
            "form": form,
        }
    return render(request, 'music/upload_album.html', context)

@login_required
def upload_song_view(request, album_id):
    form = SongForm(request.POST or None, request.FILES or None)
    album = get_object_or_404(Album, pk=album_id)
    if form.is_valid():
        albums_songs = album.song_set.all()
        for s in albums_songs:
            if s.song_title == form.cleaned_data.get("song_title"):
                context = {
                    'album': album,
                    'form': form,
                    'error_message': 'You already added that song',
                }
                return render(request, 'music/create_song.html', context)
        song = form.save(commit=False)
        song.album = album
        song.audio_file = request.FILES['audio_file']
        file_type = song.audio_file.url.split('.')[-1]
        file_type = file_type.lower()
        if file_type not in AUDIO_FILE_TYPES:
            context = {
                'album': album,
                'form': form,
                'error_message': 'Audio file must be WAV, MP3, or OGG',
            }
            return render(request, 'music/upload_song.html', context)

        song.save()
        return render(request, 'music/album_detail.html', {'album': album})
    context = {
        'album': album,
        'form': form,
    }
    return render(request, 'music/upload_song.html', context)

def album_detail_view(request, user_id, album_id):
    context_user = user_tracker(request, user_id)

    album = get_object_or_404(Album, pk=album_id)
    context_data = {'album': album}
    
    context = {**context_user, **context_data}

    return render(request, 'music/album_detail.html', context)

@login_required
def add_to_library(request, album_id):

    profile = get_object_or_404(User, id=request.user.id)

    album = Album.objects.get(pk=album_id)
    albumsongs = album.song_set.all()

    print ('--------',album.artist)
    
    album_copy = Album()
    album_copy = copy.deepcopy(album)
    album_copy.users.add(profile)
    # 
    # album_copy.song.add(album_songs)

    # print ('dddddddd',album_copy.song_set.all())
    # album_copy

    # album_copy.albums.add(album_copy)
    # profile.album
    print ('#####',type(album_copy))

    # print ("#########",album_copy.users.all())

    # album_copy.users = None

    # print ('@@@@@@@@@@',album_copy.user)

    album_copy.save()

    return render(request, 'music/my_library.html', {'profile': profile })

@login_required
def delete_album(request, album_id):
    album = Album.objects.get(pk=album_id)

    print(request.user)

    if len(album.users.all()) > 1:
        album.users.remove(request.user)
    else:
        album.delete()
    albums = Album.objects.filter(users=request.user)
    context_user = user_tracker(request, request.user.id)
    return render(request, 'music/my_library.html', context_user, {'albums': albums})
    

@login_required
def delete_song(request, album_id, song_id):
    album = get_object_or_404(Album, pk=album_id)
    song = Song.objects.get(pk=song_id)
    song.delete()
    return render(request, 'music/album_detail.html', {'album': album})

@login_required
def favorite_song(request, album_id, song_id):
    album = get_object_or_404(Album, pk=album_id)
    song = get_object_or_404(Song, pk=song_id)
    try:
        if song.is_favorite:
            song.is_favorite = False
        else:
            song.is_favorite = True
        song.save()
    except (KeyError, Song.DoesNotExist):
        return render(request, 'music/album_detail.html', {'album': album})
    else:
        return render(request, 'music/album_detail.html', {'album': album})

@login_required
def favorite_album(request, user_id, album_id):
    
    albums = Album.objects.filter(users=request.user)

    context_user = user_tracker(request, user_id)
    context_data = {'albums': albums}
    context = {**context_user, **context_data}

    album_fav = get_object_or_404(Album, pk=album_id)
    try:
        if album_fav.is_favorite:
            album_fav.is_favorite = False
        else:
            album_fav.is_favorite = True
        album_fav.save()
    except (KeyError, Album.DoesNotExist):
        return render(request, 'music/my_library.html', context)
    else:
        return render(request, 'music/my_library.html', context)
