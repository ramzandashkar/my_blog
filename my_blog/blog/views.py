from django.contrib.postgres.search import (
    SearchVector,
    SearchQuery,
    SearchRank, TrigramSimilarity,
)
from django.core.mail import send_mail
from django.core.paginator import (
    Paginator,
    EmptyPage,
    PageNotAnInteger,
)
from django.db.models import Count
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST
from taggit.models import Tag

from .forms import EmailPostForm, CommentForm, SearchForm
from .models import Post


# class PostListView(ListView):
#     queryset = Post.published.all()
#     context_object_name = 'posts'
#     paginate_by = 3
#     template_name = 'blog/post/list.html'


def post_list(request, tag_slug=None):
    template = 'blog/post/list.html'
    post_list = Post.published.all()
    tag = None
    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        post_list = post_list.filter(tags__in=[tag])
    paginator = Paginator(post_list, 3)
    page_number = request.GET.get('page', 1)
    try:
        posts = paginator.page(page_number)
    except PageNotAnInteger:
        posts = paginator.page(1)
    except EmptyPage:
        posts = paginator.page(paginator.num_pages)

    context = {
        'posts': posts,
        'tag': tag,
    }

    return render(request, template, context)


def post_share(request, post_id):
    """Отправка поста на e-mail. Retrieve post by id"""

    template = 'blog/post/share.html'
    post = get_object_or_404(Post, id=post_id, status=Post.Status.PUBLISHED)
    sent = False

    if request.method == 'POST':
        # Form was submitted
        form = EmailPostForm(request.POST)
        if form.is_valid():
            # Form fields passed validation
            cd = form.cleaned_data
            post_url = request.build_absolute_uri(post.get_absolute_url())
            subject = f"{cd['name']} recommends you read " \
                      f"{post.title}"
            message = f"Read {post.title} at {post_url}\n\n" \
                      f"{cd['name']}\'s comments: {cd['comments']}"
            send_mail(subject, message, 'sirius712@mail.ru',
                      [cd['to']])
            sent = True

    else:
        form = EmailPostForm()

    context = {
        'post': post,
        'form': form,
        'sent': sent,
    }

    return render(request, template, context)


def post_detail(request, year, month, day, post):
    """Детальное описание поста"""

    template = 'blog/post/detail.html'
    post = get_object_or_404(
        Post,
        status=Post.Status.PUBLISHED,
        slug=post,
        publish__year=year,
        publish__month=month,
        publish__day=day,
    )
    comments = post.comments.filter(active=True)
    form = CommentForm()

    # Список схожих постов
    post_tags_ids = post.tags.values_list('id', flat=True)
    similar_posts = Post.published.filter(tags__in=post_tags_ids).exclude(id=post.id)
    similar_posts = similar_posts.annotate(same_tags=Count('tags')).order_by('-same_tags', '-publish')[:4]

    context = {
        'post': post,
        'comments': comments,
        'form': form,
        'similar_posts': similar_posts,
    }

    return render(request, template, context)


@require_POST
def post_comment(request, post_id):
    """Комментарии поста"""

    template = 'blog/post/comment.html'
    post = get_object_or_404(
        Post,
        id=post_id,
        status=Post.Status.PUBLISHED,
    )
    comment = None
    form = CommentForm(data=request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.save()

    context = {
        'post': post,
        'form': form,
        'comment': comment,
    }

    return render(request, template, context)


# def post_search(request):
#     """Поисковые запросы по постам"""
#
#     template = 'blog/post/search.html'
#     form = SearchForm()
#     query = None
#     results = []
#
#     if 'query' in request.GET:
#         form = SearchForm(request.GET)
#         if form.is_valid():
#             query = form.cleaned_data['query']
#             search_vector = SearchVector('title', 'body', weight='A', config='russian') + SearchVector('body', weight='B')
#             search_query = SearchQuery(query, config='russian')
#             results = Post.published.annotate(
#                 search=search_vector,
#                 rank=SearchRank(search_vector, search_query)
#             ).filter(rank__gte=0.3).filter(search=search_query).order_by('-rank')
#
#     context = {
#             'form': form,
#             'query': query,
#             'results': results,
#     }
#
#     return render(request, template, context)


def post_search(request):
    """Поисковые запросы по постам"""

    template = 'blog/post/search.html'
    form = SearchForm()
    query = None
    results = []

    if 'query' in request.GET:
        form = SearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data['query']
            results = Post.published.annotate(
                similarity=TrigramSimilarity('title', query),
            ).filter(similarity__gt=0.1).order_by('-similarity')

    context = {
            'form': form,
            'query': query,
            'results': results,
    }

    return render(request, template, context)