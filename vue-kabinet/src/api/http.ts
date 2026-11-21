export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    /** Field errors from a 422 response */
    public fields: Record<string, string> = {},
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

type Method = 'GET' | 'POST' | 'PATCH' | 'DELETE'

let token: string | null = null

export function setToken(value: string | null) {
  token = value
}

/** Thin wrapper over fetch: JSON in and out, auth header, readable errors */
export async function request<T>(method: Method, url: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers.Authorization = `Bearer ${token}`

  let response: Response
  try {
    response = await fetch(url, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new ApiError(0, 'Нет связи с сервером')
  }

  const data = response.status === 204 ? null : await response.json().catch(() => null)
  if (!response.ok) {
    throw new ApiError(response.status, data?.message ?? `Ошибка ${response.status}`, data?.errors)
  }
  return data as T
}

export function toQueryString(params: Record<string, string | number | boolean>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== '' && value !== undefined) search.set(key, String(value))
  }
  const text = search.toString()
  return text ? `?${text}` : ''
}
