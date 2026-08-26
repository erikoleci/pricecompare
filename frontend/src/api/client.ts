import axios from 'axios'

export const apiClient = axios.create({
  baseURL: '/api',
  timeout: 10000
})

export interface Offer {
  offerId: string
  merchantId: string
  merchantName: string
  merchantLogoUrl?: string
  price: number
  shippingCost: number | null
  totalPrice: number
  currency: string
  availability: string
  url: string
  lastSeenAt: string
}

export interface Product {
  id: string
  title: string
  normalizedTitle: string
  description?: string
  status: string
}

export interface PriceStats {
  current: number | null
  lowest: number | null
  highest: number | null
  average: number | null
  lowestDate: string | null
  highestDate: string | null
}

export const productsApi = {
  list: (params?: Record<string, unknown>) => apiClient.get<Product[]>('/products', { params }),
  get: (id: string) => apiClient.get<Product>(`/products/${id}`),
  offers: (id: string, sort: 'lowest_price' | 'highest_price' = 'lowest_price') =>
    apiClient.get<Offer[]>(`/products/${id}/offers`, { params: { sort } }),
  priceHistory: (id: string, range: '7d' | '30d' | '90d' | '6m' | '1y' | 'all' = '30d') =>
    apiClient.get<PriceStats>(`/products/${id}/price-history`, { params: { range } })
}
