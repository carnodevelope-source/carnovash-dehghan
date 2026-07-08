import home from '../assets/iconly/home.svg'
import users3 from '../assets/iconly/users-3.svg'
import document from '../assets/iconly/document.svg'
import calendar from '../assets/iconly/calendar.svg'
import setting from '../assets/iconly/setting.svg'
import wallet from '../assets/iconly/wallet.svg'
import chat from '../assets/iconly/chat.svg'
import search from '../assets/iconly/search.svg'
import filter from '../assets/iconly/filter.svg'
import plus from '../assets/iconly/plus.svg'
import editSquare from '../assets/iconly/edit-square.svg'
import trash from '../assets/iconly/delete.svg'
import logout from '../assets/iconly/logout.svg'
import profile from '../assets/iconly/profile.svg'
import graph from '../assets/iconly/graph.svg'
import category from '../assets/iconly/category.svg'
import message from '../assets/iconly/message.svg'
import show from '../assets/iconly/show.svg'
import buy from '../assets/iconly/buy.svg'
import paperPlus from '../assets/iconly/paper-plus.svg'

export const iconlyIcons = {
  home,
  users3,
  document,
  calendar,
  setting,
  wallet,
  chat,
  search,
  filter,
  plus,
  editSquare,
  trash,
  logout,
  profile,
  graph,
  category,
  message,
  show,
  buy,
  paperPlus
}

export const iconSrc = (name) => iconlyIcons[name] || ''
