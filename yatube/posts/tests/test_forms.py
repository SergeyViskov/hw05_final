import shutil
import tempfile

from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client, override_settings
from django.urls import reverse

from posts.models import Post, Group, Comment

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
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

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.author_client = Client()
        self.author_client.force_login(self.user)

    def test_create_post_form(self):
        """Валидная форма создает новый объект Post."""
        post_count = Post.objects.count()
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
        form_data = {
            'text': self.post.text,
            'group': self.group.pk,
            'image': uploaded,
        }
        response = self.author_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('posts:profile',
                    kwargs={'username': self.user.username})
        )
        self.assertEqual(Post.objects.count(), post_count + 1)
        post = Post.objects.latest('id')
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.group.id, form_data['group'])
        self.assertEqual(post.image.name, 'posts/small.gif')

    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        post_count = Post.objects.count()
        form_data = {
            'text': self.post.text,
            'group': self.group.pk
        }
        response = self.author_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True,
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertRedirects(
            response, reverse('posts:profile', args=[self.user.username]))
        self.assertEqual(Post.objects.count(), post_count + 1)
        last_object = Post.objects.order_by('-id').first()
        self.assertEqual(form_data['text'], last_object.text)
        self.assertEqual(form_data['group'], last_object.group.pk)

    def test_post_edit(self):
        new_text = 'Новый тестовый текст'
        form_data = {
            'text': new_text,
            'group': self.group.pk
        }
        response = self.author_client.post(
            reverse('posts:post_edit', args=[self.post.id]),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response, reverse('posts:post_detail', args=[self.post.id]))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.post.refresh_from_db()
        self.assertEqual(form_data['text'], self.post.text)
        self.assertEqual(form_data['group'], self.group.pk)


class CommentFormTests(TestCase):
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
            group=cls.group
        )
        cls.comment = Comment.objects.create(
            author=cls.user,
            text='Тестовый текст',
            post=cls.post
        )

    def setUp(self):
        self.guest_client = Client()
        self.author_client = Client()
        self.author_client.force_login(self.user)

    def test_add_comment(self):
        """Валидная форма создает запись в Post."""
        comment_count = Comment.objects.count()
        form_data = {
            'text': 'Тестовый комментарий',
        }
        response = self.author_client.post(
            reverse('posts:add_comment', args=[self.post.id]),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response, reverse('posts:post_detail', args=[self.post.id]))
        self.assertEqual(Comment.objects.count(), comment_count + 1)
        self.assertTrue(
            Comment.objects.filter(
                text='Тестовый комментарий',
            ).exists()
        )
