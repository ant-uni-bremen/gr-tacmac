/* -*- c++ -*- */
/*
 * Copyright 2020 Johannes Demel.
 *
 * This is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 3, or (at your option)
 * any later version.
 *
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this software; see the file COPYING.  If not, write to
 * the Free Software Foundation, Inc., 51 Franklin Street,
 * Boston, MA 02110-1301, USA.
 */

#ifndef INCLUDED_TACMAC_UTILITIES_H
#define INCLUDED_TACMAC_UTILITIES_H

#include <cstdint>
#include <memory>
#include <stdexcept>
#include <string>
#include <pmt/pmt.h>

namespace gr {
namespace tacmac {

/*
 * This is a C++11 solution to obtain formatted strings.
 *
 * Source: https://stackoverflow.com/a/26221725 under CC0
 *
 * As noted in the source this boils down to:
 * std::format() with C++20!
 */
template <typename... Args>
std::string string_format(const std::string& format, Args... args)
{
    size_t size =
        snprintf(nullptr, 0, format.c_str(), args...) + 1; // Extra space for '\0'
    if (size <= 0) {
        throw std::runtime_error("Error during formatting.");
    }
    std::unique_ptr<char[]> buf(new char[size]);
    snprintf(buf.get(), size, format.c_str(), args...);
    return std::string(buf.get(), buf.get() + size - 1); // We don't want the '\0' inside
}

inline uint64_t double2ticks(const double interval)
{
    return uint64_t(1000000000ull * interval);
}

inline uint64_t timespec2ticks(const uint64_t full_secs, const double frac_secs)
{
    return 1000000000ull * full_secs + double2ticks(frac_secs);
}

inline uint64_t ticks2fullsecs(const uint64_t ticks) { return ticks / 1000000000ull; }

inline double ticks2fracsecs(const uint64_t ticks)
{
    return double(ticks % 1000000000ull) / 1000000000.0d;
}

inline pmt::pmt_t flatten_dict(const pmt::pmt_t& dict)
{
    auto res = pmt::make_dict();
    // only unwrap 1 layer! This is intentionally non-recursive!
    for (size_t i = 0; i < pmt::length(dict); i++) {
        auto k = pmt::car(pmt::nth(i, dict));
        auto v = pmt::cdr(pmt::nth(i, dict));
        if (pmt::is_dict(v)) {
            res = pmt::dict_update(res, v);
        } else {
            res = pmt::dict_add(res, k, v);
        }
    }

    return res;
}

} // namespace tacmac
} // namespace gr

#endif /* INCLUDED_TACMAC_UTILITIES_H */
