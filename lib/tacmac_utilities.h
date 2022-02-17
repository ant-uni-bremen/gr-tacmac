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

#include <fmt/core.h>
#include <pmt/pmt.h>
#include <chrono>
#include <cstdint>
#include <memory>
#include <regex>
#include <stdexcept>
#include <string>

namespace gr {
namespace tacmac {

inline uint64_t get_timestamp_ticks_ns_now()
{
    return std::chrono::high_resolution_clock::now().time_since_epoch().count();
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
            auto key_str = pmt::symbol_to_string(k);
            bool holds_number = true;
            int number = 0;
            try {
                auto numeric_str =
                    std::regex_replace(key_str, std::regex(R"([^\d])"), "");
                number = std::stoi(numeric_str);
            } catch (const std::exception&) {
                // catch all and ignore this try...
                holds_number = false;
            }

            if (holds_number) {
                for (size_t j = 0; j < pmt::length(v); j++) {
                    auto ik = pmt::car(pmt::nth(j, v));
                    auto nextkey = fmt::format("{}{}", pmt::symbol_to_string(ik), number);
                    auto iv = pmt::cdr(pmt::nth(j, v));
                    res = pmt::dict_add(res, pmt::string_to_symbol(nextkey), iv);
                }
            } else {
                res = pmt::dict_update(res, v);
            }

        } else {
            res = pmt::dict_add(res, k, v);
        }
    }

    return res;
}

} // namespace tacmac
} // namespace gr

#endif /* INCLUDED_TACMAC_UTILITIES_H */
