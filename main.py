from flask import Flask, render_template, redirect, url_for, request, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_login import login_user, UserMixin, LoginManager, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy.orm import relationship
from functools import wraps
from flask_gravatar import Gravatar
app = Flask(__name__)
app.secret_key = "TheBillionareWaqi"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///blog.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
Bootstrap(app)
CKEditor(app)
gravatar = Gravatar(app, size=100, rating='g', default='retro', force_default=False, force_lower=False, use_ssl=False, base_url=None)
login_manager = LoginManager()
login_manager.init_app(app)


class Users(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(500), nullable=False)
    name = db.Column(db.String(250))
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="author_comment")


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    author = relationship("Users", back_populates="posts")
    comments = relationship("Comment", back_populates="parent_post")


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    author_comment = relationship("Users", back_populates="comments")
    parent_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    parent_post = relationship("BlogPost", back_populates="comments")
    text = db.Column(db.Text, nullable=False)


with app.app_context():
    db.create_all()


def admin_only(function):
    @wraps(function)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.id != 1:
            return abort(403)
        # if current_user.id == 1:
        #     return function(*args, **kwargs)
        # else:
        #     return abort(403)
        return function(*args, **kwargs)
    return decorated_function


@login_manager.user_loader
def load_user(id_number):
    return Users.query.get(int(id_number))


@app.route("/")
def get_all_posts():
    blog_posts = BlogPost.query.all()
    return render_template("index.html", all_posts=blog_posts, logged_in=current_user.is_authenticated)


@app.route("/posts", methods=["GET", "POST"])
def show_post():
    post_number = request.args.get("post_id")
    comment = CommentForm()
    if comment.validate_on_submit():
        if current_user.is_authenticated:
            new_comment = Comment(author_id=current_user.id, parent_id=post_number, text=comment.comment.data)
            db.session.add(new_comment)
            db.session.commit()
        else:
            flash("Login Required!")
            return redirect(url_for("login"))
    blog_post = BlogPost.query.get(post_number)
    return render_template("post.html", post=blog_post, logged_in=current_user.is_authenticated,
                           comment_form=comment)


@app.route("/edit", methods=["GET", "POST"])
@admin_only
def edit_post():
    post = BlogPost.query.get(request.args.get("post_id"))
    form = CreatePostForm(title=post.title, subtitle=post.subtitle, img_url=post.img_url, body=post.body)
    if form.validate_on_submit():
        post.title = form.title.data
        post.subtitle = form.subtitle.data
        post.img_url = form.img_url.data
        post.body = form.body.data
        post.author_id = current_user.id
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make-post.html", is_edit=True, form=form)


@app.route("/delete")
@admin_only
def delete_post():
    blog_post = BlogPost.query.get(request.args.get("post_id"))
    db.session.delete(blog_post)
    db.session.commit()
    return redirect(url_for("get_all_posts"))


@app.route("/add", methods=["GET", "POST"])
@admin_only
def add_new_post():
    post_form = CreatePostForm()
    if post_form.validate_on_submit():
        new_post = BlogPost(title=post_form.title.data, subtitle=post_form.subtitle.data,
                            img_url=post_form.img_url.data, body=post_form.body.data,
                            date=datetime.now().strftime("%B %d, %Y"), author_id=current_user.id)
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=post_form)


@app.route("/login", methods=["GET", "POST"])
def login():
    login_form = LoginForm()
    if login_form.validate_on_submit():
        user = Users.query.filter_by(email=login_form.email.data).first()
        password = login_form.password.data
        if not user:
            flash("The Email You Entered does not Exist please Register now!")
            return render_template("login.html", form=login_form)
        elif not check_password_hash(user.password, password):
            flash("Incorrect Password!")
            return render_template("login.html", form=login_form)
        else:
            login_user(user)
            return redirect(url_for("get_all_posts"))
    return render_template("login.html", form=login_form)


@app.route("/register", methods=["GET", "POST"])
def register():
    registration = RegisterForm()
    if registration.validate_on_submit():
        user = Users.query.filter_by(email=registration.email.data).first()
        if user:
            flash("The email you are trying to register is already exist please login!")
            return redirect(url_for("login"))
        else:
            new_user = Users(email=registration.email.data,
                             password=generate_password_hash(registration.password.data, salt_length=8),
                             name=registration.name.data)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for("get_all_posts"))
    return render_template("register.html", form=registration)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("get_all_posts"))


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)