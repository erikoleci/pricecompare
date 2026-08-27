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

export interface SearchResult {
  productId: string
  title: string
  brandName: string | null
  categoryName: string | null
  categorySlug: string | null
  lowestTotalPrice: number | null
  merchantCount: number
  matchType: 'EAN' | 'GTIN' | 'MPN' | 'SKU' | 'FULLTEXT' | 'FUZZY'
}

export interface CompareProduct {
  productId: string
  title: string
  brandName: string | null
  currentPrice: number | null
  lowestPrice: number | null
  averagePrice: number | null
  merchantCount: number
  averageRating: number | null
  reviewCount: number | null
  specifications: Record<string, string>
}

export interface CategoryFilter {
  key: string
  label: string
  type: 'multi_select' | 'boolean' | 'range'
  source: string
  options?: string[]
}

export interface Category {
  id: string
  slug: string
  name: string
  filterSchema?: { filters: CategoryFilter[] } | string[] | null
}

export const productsApi = {
  list: (params?: Record<string, unknown>) => apiClient.get<Product[]>('/products', { params }),
  get: (id: string) => apiClient.get<Product>(`/products/${id}`),
  offers: (id: string, sort: 'lowest_price' | 'highest_price' = 'lowest_price') =>
    apiClient.get<Offer[]>(`/products/${id}/offers`, { params: { sort } }),
  priceHistory: (id: string, range: '7d' | '30d' | '90d' | '6m' | '1y' | 'all' = '30d') =>
    apiClient.get<PriceStats>(`/products/${id}/price-history`, { params: { range } }),
  compare: (ids: string[]) =>
    apiClient.get<CompareProduct[]>('/products/compare', { params: { ids } })
}

export const searchApi = {
  search: (params: { q: string; category?: string; brand?: string; page?: number; size?: number }) =>
    apiClient.get<SearchResult[]>('/search', { params })
}

export const categoriesApi = {
  list: () => apiClient.get<Category[]>('/categories'),
  get: (slug: string) => apiClient.get<Category>(`/categories/${slug}`)
}
