from flask_restplus import fields
from server.instance import server

login_post = server.api.model('Login Payload', {
    'username': fields.String(
        required=True,
        description='Username',
        example='JohnDoe'
    ),
    'password': fields.String(
        required=True,
        description='Password',
        example='MyStrongPassword'
    )
})

login_response = server.api.model('Login Response', {
    'access_token': fields.String(
        example='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c'
    )
})
