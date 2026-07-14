import api from './api'

// register a new account
// returns the created user object
export const register = async (username, email, password) => {
  const res = await api.post('/auth/register', { username, email, password })
  return res.data
}

// login and get back a JWT token
export const login = async (email, password) => {
  const res = await api.post('/auth/login', { email, password })
  return res.data  // { access_token, token_type }
}

// fetch the logged-in user's profile
// used on app load to restore session
export const getMe = async () => {
  const res = await api.get('/auth/me')
  return res.data
}
