import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Group, Post, Comment, Follow

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовый тайтл',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст',
        )

    def setUp(self):
        self.author_client = Client()
        self.author_client.force_login(self.user)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:group_posts',
                    args=[self.group.slug]): 'posts/group_list.html',
            reverse('posts:profile',
                    args=[self.user.username]): 'posts/profile.html',
            reverse('posts:post_detail',
                    args=[self.post.id]): 'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit',
                    args=[self.post.id]): 'posts/create_post.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.author_client.get(reverse_name)
                self.assertTemplateUsed(response, template)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(
            username='auth',
        )
        cls.group = Group.objects.create(
            title='Тестовое название группы',
            slug='test_slug',
            description='Тестовое описание группы',
        )
        for i in range(13):
            Post.objects.create(
                text=f'Пост #{i}',
                author=cls.user,
                group=cls.group
            )

    def setUp(self):
        self.unauthorized_client = Client()

    def test_paginator_on_pages(self):
        """Проверка пагинации на страницах."""
        posts_on_first_page = settings.AMOUNT_POSTS
        posts_on_second_page = Post.objects.count() % settings.AMOUNT_POSTS
        url_pages = [
            reverse('posts:index'),
            reverse('posts:group_posts', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user.username}),
        ]
        for reverse_ in url_pages:
            with self.subTest(reverse_=reverse_):
                self.assertEqual(len(self.unauthorized_client.get(
                    reverse_).context.get('page_obj')),
                    posts_on_first_page
                )
                self.assertEqual(len(self.unauthorized_client.get(
                    reverse_ + '?page=2').context.get('page_obj')),
                    posts_on_second_page
                )


class PostContextTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовый тайтл',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст',
            group=cls.group,
        )

    def setUp(self):
        self.author_client = Client()
        self.author_client.force_login(self.user)

    def test_post_posts_groups_page_show_correct_context(self):
        """Проверяем Context страницы posts_groups"""
        response = self.author_client.get(
            reverse('posts:group_posts', kwargs={'slug': self.group.slug}))
        for post in response.context['page_obj']:
            self.assertEqual(post.group, self.group)

    def test_post_profile_page_show_correct_context(self):
        """Проверяем Context страницы profile"""
        response = self.author_client.get(
            reverse('posts:profile', kwargs={'username': self.user.username}))
        for post in response.context['page_obj']:
            self.assertEqual(post.author, self.user)

    def test_post_detail_page_show_correct_context(self):
        """Шаблон posts:post_detail сформирован с правильным контекстом"""
        response = self.author_client.get(
            reverse('posts:post_detail', args=[self.post.id]))
        current_object = response.context['post']
        post_id = current_object.id
        self.assertEqual(post_id, self.post.id)

    def test_create_post_show_correct_context(self):
        """Шаблон post:post_create сформирован с правильным контекстом"""
        response = self.author_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_edit_post_show_correct_context(self):
        """Шаблон post:post_edit сформирован с правильным контекстом"""
        response = self.author_client.get(
            reverse('posts:post_edit', args=[self.post.id]))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                is_edit_field = response.context.get('is_edit')
                self.assertIsInstance(form_field, expected)
                self.assertEqual(is_edit_field, True)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostImageExistTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.user = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовый тайтл',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group,
            image=uploaded,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.author_client = Client()
        self.author_client.force_login(self.user)

    def test_post_with_image_exist(self):
        self.assertTrue(Post.objects.filter(image='posts/small.gif'))

    def test_index_show_correct_image_in_context(self):
        """В Шаблоне index картинка передается в словаре context"""
        cache.clear()
        response = self.author_client.get(reverse('posts:index'))
        test_object = response.context['page_obj'][0]
        post_image = test_object.image
        self.assertEqual(post_image, 'posts/small.gif')

    def test_post_detail_image_exist(self):
        """В шаблоне post_detail картинка передается в словаре context"""
        response = self.author_client.get(
            reverse('posts:post_detail', args=[self.post.id])
        )
        test_object = response.context['post']
        post_image = test_object.image
        self.assertEqual(post_image, 'posts/small.gif')

    def test_group_and_profile_image_exist(self):
        """В шаблонах group и profile картинка передается в словаре context"""
        templates_pages_name = {
            'posts:group_posts': self.group.slug,
            'posts:profile': self.user.username,
        }
        for names, args in templates_pages_name.items():
            with self.subTest(names=names):
                response = self.author_client.get(reverse(names, args=[args]))
                test_object = response.context['page_obj'][0]
                post_image = test_object.image
                self.assertEqual(post_image, 'posts/small.gif')

    def test_add_comment_authorized_user(self):
        """
        Добавление комментария к посту авторизованным пользователем.
        """
        post = Post.objects.first()
        comment = Comment.objects.create(
            post=post,
            author=self.user,
            text='Комментарий',
        )
        response = self.author_client.get(
            reverse(
                'posts:post_detail',
                kwargs={'post_id': post.id})
        )
        self.assertEqual(response.context['comments'][0].post, comment.post)
        self.assertEqual(response.context['comments'][0].author,
                         comment.author)
        self.assertEqual(response.context['comments'][0].text, comment.text)


class CacheTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.author_client = Client()
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый текст',
        )

    def test_caching(self):
        """Проверка кеширования главной страницы"""
        cache.clear()
        response = self.author_client.get(reverse('posts:index'))
        posts_count = Post.objects.count()
        self.post.delete
        self.assertEqual(len(response.context['page_obj']), posts_count)
        cache.clear()
        posts_count = Post.objects.count()
        self.assertEqual(len(response.context['page_obj']), posts_count)


class FollowViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.post_autor = User.objects.create(
            username='post_autor',
        )
        cls.post_follower = User.objects.create(
            username='post_follower',
        )
        cls.post = Post.objects.create(
            text='Подпишись на меня',
            author=cls.post_autor,
        )

    def setUp(self):
        cache.clear()
        self.author_client = Client()
        self.author_client.force_login(self.post_follower)
        self.follower_client = Client()
        self.follower_client.force_login(self.post_autor)

    def test_follow_on_user(self):
        """Проверка подписки на пользователя."""
        count_follow = Follow.objects.count()
        self.follower_client.post(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.post_follower}))
        follow = Follow.objects.all().latest('id')
        self.assertEqual(Follow.objects.count(), count_follow + 1)
        self.assertEqual(follow.author_id, self.post_follower.id)
        self.assertEqual(follow.user_id, self.post_autor.id)

    def test_unfollow_on_user(self):
        """Проверка отписки от пользователя."""
        Follow.objects.create(
            user=self.post_autor,
            author=self.post_follower)
        count_follow = Follow.objects.count()
        self.follower_client.post(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': self.post_follower}))
        self.assertEqual(Follow.objects.count(), count_follow)

    def test_follow_on_authors(self):
        """Проверка записей у тех кто подписан."""
        post = Post.objects.create(
            author=self.post_autor,
            text="Подпишись на меня")
        Follow.objects.create(
            user=self.post_follower,
            author=self.post_autor)
        response = self.author_client.get(
            reverse('posts:follow_index'))
        self.assertIn(post, response.context['page_obj'].object_list)

    def test_notfollow_on_authors(self):
        """Проверка записей у тех кто не подписан."""
        post = Post.objects.create(
            author=self.post_autor,
            text="Подпишись на меня")
        response = self.author_client.get(
            reverse('posts:follow_index'))
        self.assertNotIn(post, response.context['page_obj'].object_list)
